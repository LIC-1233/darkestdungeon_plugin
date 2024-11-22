import logging
import os
import random
import re
import shutil
from pathlib import Path
from typing import Sequence
from xml.etree import ElementTree as ET
from xml.etree.ElementTree import Element

import mobase
import vdf  # type: ignore
from PyQt6.QtCore import QModelIndex, Qt
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (
    QHeaderView,
    QInputDialog,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressDialog,
    QTableView,
    QWidget,
)

from .steam_utils import find_games, find_steam_path, parse_library_info
from .table_copy import ButtonDelegate, MyTableModel

logger = logging.getLogger()

# QProgressDialog 到时候复制文件用这个，带进度条和取消


class dd_xml_data:
    mod_title: str
    mod_versions: list[int]
    mod_tags: list[str]
    mod_description: str
    mod_PublishedFileId: str

    def __init__(
        self,
        mod_title: str,
        mod_versions: list[int],
        mod_tags: list[str],
        mod_description: str,
        mod_PublishedFileId: str,
    ):
        self.mod_title = mod_title
        self.mod_versions = mod_versions
        self.mod_tags = mod_tags
        self.mod_description = mod_description
        self.mod_PublishedFileId = mod_PublishedFileId

    @classmethod
    def etree_text_iter(cls, tree: Element, name: str):
        for elem in tree.iter(name):
            if isinstance(elem.text, str):
                return elem.text
        return ""

    @classmethod
    def mod_xml_parser(cls, xml_file: str | Path):
        mod_title: str = ""
        mod_versions: list[int] = [0, 0, 0]
        mod_tags: list[str] = []
        mod_description: str = ""
        mod_PublishedFileId: str = ""
        try:
            tree = ET.fromstring(
                Path(xml_file).read_text(encoding="utf-8", errors="ignore").strip()
            )
            root = tree
            mod_title = cls.etree_text_iter(root, "Title") or mod_title
            mod_title = re.sub(r'[\/:*?"<>|]', "_", mod_title).strip()
            mod_versions[0] = int(
                cls.etree_text_iter(root, "VersionMajor") or mod_versions[0]
            )
            mod_versions[1] = int(
                cls.etree_text_iter(root, "VersionMinor") or mod_versions[1]
            )
            mod_versions[2] = int(
                cls.etree_text_iter(root, "TargetBuild") or mod_versions[2]
            )
            mod_description = (
                cls.etree_text_iter(root, "ItemDescription") or mod_description
            )
            mod_PublishedFileId = (
                cls.etree_text_iter(root, "PublishedFileId") or mod_PublishedFileId
            )
            for Tags in root.iter("Tags"):
                if not isinstance(Tags.text, str) or not Tags.text.strip():
                    continue
                mod_tags.append(Tags.text)
        except Exception:
            pass
        return cls(
            mod_title, mod_versions, mod_tags, mod_description, mod_PublishedFileId
        )


class DarkestDungeonModCopy(mobase.IPluginTool):
    def __init__(self):
        super(DarkestDungeonModCopy, self).__init__()
        self._organizer: mobase.IOrganizer
        self.__parentWidget: QWidget
        self.model: MyTableModel
        self.data: list[list[str]] = []
        self.workshop_items: dict[str, dict[str, str]] = {}
        pass

    def init(self, organizer: mobase.IOrganizer):
        self._organizer: mobase.IOrganizer = organizer
        return True

    def setParentWidget(self, parent: QWidget):
        self.__parentWidget: QWidget = parent

    def requirements(self) -> list[mobase.IPluginRequirement]:
        return [mobase.PluginRequirementFactory.gameDependency("Darkest Dungeon")]

    def display(self) -> None:
        windows = QMainWindow(self.__parentWidget)
        windows.setWindowTitle("Darkest Dungeon Mod Copy")
        windows.setGeometry(100, 100, 1720, 900)  # 设置窗口位置和大小
        self.table_view = QTableView()
        self.init_data()
        self.table_view.setColumnWidth(0, 600)
        self.table_view.setColumnWidth(1, 200)
        self.table_view.setColumnWidth(2, 10)
        self.table_view.setColumnWidth(3, 10)
        self.table_view.setColumnWidth(4, 200)
        self.table_view.setColumnWidth(5, 600)
        self.table_view.hideColumn(6)
        self.table_view.hideColumn(2)
        if horizontalHeader := self.table_view.horizontalHeader():
            horizontalHeader.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
            horizontalHeader.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        if verticalHeader := self.table_view.verticalHeader():
            verticalHeader.setDefaultSectionSize(10)
        self.table_view.setShowGrid(False)
        windows.setCentralWidget(self.table_view)
        if verticalHeader := self.table_view.verticalHeader():
            verticalHeader.setVisible(False)
        windows.show()
        pass

    def _get_workshop_path(self):
        workshop_paths: list[Path] = []
        steam_path = find_steam_path()
        if steam_path is not None:
            library_folders = parse_library_info(
                steam_path / "steamapps" / "libraryfolders.vdf"
            )
            for library_folder in library_folders:
                acf_file = (
                    library_folder.path
                    / "steamapps"
                    / "workshop"
                    / "appworkshop_262060.acf"
                )
                if acf_file.exists():
                    workshop_paths.append(
                        library_folder.path / "steamapps" / "workshop"
                    )
        else:
            workshop_paths.append(find_games()["262060"].parent.parent / "workshop")
        logger.debug(f"Found {len(workshop_paths)} workshop: {workshop_paths}")
        return workshop_paths

    def get_workshop_items(self):
        workshop_path_workshop_items: dict[Path, dict[str, dict[str, str]]] = {}
        for workshop_path in self._get_workshop_path():
            acf_path = workshop_path / "appworkshop_262060.acf"
            if acf_path.exists():
                workshop_path_workshop_items[workshop_path] = vdf.load(open(acf_path))[  # type: ignore
                    "AppWorkshop"
                ]["WorkshopItemDetails"]
                logger.debug(
                    f"found {len(workshop_path_workshop_items[workshop_path])} mod-records in {workshop_path}"
                )
                for i in workshop_path_workshop_items.values():
                    self.workshop_items.update(i)
            else:
                logger.debug(f"darkest_dungeon acf file not exist in {workshop_path}")
        mod_list = self._organizer.modList()
        mo_workshop_PublishedFileId: dict[str, mobase.IModInterface] = {
            str(i.stem.strip("w")): mod_list.getMod(str(i.parent.parent.name))
            for i in Path(self._organizer.modsPath()).glob("*/project_file/w*.manifest")
        }
        data: list[list[str]] = []
        for game_workshop_path, workshop_items in workshop_path_workshop_items.items():
            for PublishedFileId in workshop_items.keys():
                xml_data = dd_xml_data.mod_xml_parser(
                    game_workshop_path
                    / "content"
                    / "262060"
                    / PublishedFileId
                    / "project.xml"
                )
                data.append(
                    [
                        str(
                            (
                                game_workshop_path
                                / "content"
                                / "262060"
                                / PublishedFileId
                            ).absolute()
                        ),
                        xml_data.mod_title,
                        " 1" if PublishedFileId in mo_workshop_PublishedFileId else "",
                        "",
                        "尚未复制"
                        if PublishedFileId not in mo_workshop_PublishedFileId
                        else mo_workshop_PublishedFileId[PublishedFileId].name(),
                        "尚未复制"
                        if PublishedFileId not in mo_workshop_PublishedFileId
                        else mo_workshop_PublishedFileId[
                            PublishedFileId
                        ].absolutePath(),
                        "1",
                    ]
                )
        data = sorted(data, key=lambda x: x[5], reverse=True)
        return data

    def handleButtonClicked(self, index: QModelIndex):
        input = QInputDialog(self.__parentWidget, Qt.WindowType.Dialog)
        text, ok = input.getText(
            self.__parentWidget,
            "模组安装",
            "模组名",
            QLineEdit.EchoMode.Normal,
            self.data[index.row()][1],
        )
        # input.show()
        if ok:
            text: str = text.strip()
            if self.is_valid_filename(text):
                if text not in self._organizer.modList().allModsByProfilePriority():
                    self.scopy_mod(
                        Path(self.data[index.row()][0]),
                        Path(self._organizer.modsPath()) / text,
                        self.data[index.row()][6] == "1",
                    )
                    self.model.setData(self.model.index(index.row(), 5), text)  # TODO
                    self.model.setData(
                        self.model.index(index.row(), 5),
                        str(Path(self._organizer.modsPath()) / text),
                    )  # TODO
                    # self.model.dataChanged(self.model.index(index.row(), 5),)
                    input.close()
                else:
                    QMessageBox.critical(
                        self.__parentWidget,
                        "模组名错误",
                        "模组已存在",
                    )
            else:
                QMessageBox.critical(
                    self.__parentWidget,
                    "模组名错误",
                    "模组名含有非法字符",
                )

    def is_valid_filename(self, filename: str):
        """
        验证给定的字符串是否是有效的文件名。

        参数:
        filename (str): 要验证的文件名。

        返回:
        bool: 如果文件名有效，则返回 True；否则返回 False。
        """

        # 检查文件名是否为空
        if not filename:
            return False

        # 检查文件名是否包含非法字符
        # Windows: \ / : * ? " < > |
        # Unix: /
        illegal_chars = r'[\\/:*?"<>|]'
        if re.search(illegal_chars, filename):
            return False

        # 检查文件名是否以空格或点开头
        if filename.startswith(" ") or filename.startswith("."):
            return False

        # 检查文件名是否以空格结尾
        if filename.endswith(" "):
            return False

        # 检查文件名长度是否超过操作系统限制
        max_length = 255  # 常见的最大文件名长度限制
        if len(filename) > max_length:
            return False

        # 检查文件名是否为保留名称（Windows 特定）
        reserved_names = [
            "CON",
            "PRN",
            "AUX",
            "NUL",
            "COM1",
            "COM2",
            "COM3",
            "COM4",
            "COM5",
            "COM6",
            "COM7",
            "COM8",
            "COM9",
            "LPT1",
            "LPT2",
            "LPT3",
            "LPT4",
            "LPT5",
            "LPT6",
            "LPT7",
            "LPT8",
            "LPT9",
        ]
        if os.name == "nt":
            name, _ext = os.path.splitext(filename)
            if name.upper() in reserved_names:
                return False

        return True

    def scopy_mod(self, source: Path, dest: Path, is_from_workshop: bool):
        folders: list[Path] = []
        files: list[Path] = []
        for i in source.rglob("*"):
            if i.is_file():
                files.append(i)
            else:
                folders.append(i)
        numFiles = len(folders) + len(files)
        progress = QProgressDialog(
            "复制文件...",
            "终止",
            0,
            numFiles,
            self.__parentWidget,
            Qt.WindowType.Dialog,
        )
        dest.mkdir(exist_ok=True, parents=True)
        for i in range(len(folders)):
            progress.setLabelText(f"正在复制: {folders[i]}")
            (dest / folders[i].relative_to(source)).mkdir(exist_ok=True, parents=True)
            if progress.wasCanceled():
                break
            progress.setValue(i + 1)
        for i in range(len(files)):
            progress.setLabelText(f"正在复制: {files[i]}")
            shutil.copy2(files[i], dest / files[i].relative_to(source))
            if progress.wasCanceled():
                break
            progress.setValue(i + len(folders) + 1)
        if is_from_workshop:
            PublishedFileId = dd_xml_data.mod_xml_parser(
                source / "project.xml"
            ).mod_PublishedFileId
            mo_mod_folder = dest
            log_file = mo_mod_folder / "steam_workshop_uploader.log"
            txt_file = mo_mod_folder / "modfiles.txt"
            xml_file = mo_mod_folder / "project.xml"
            preview_file = mo_mod_folder / "preview_icon.png"
            manifest_file = (
                mo_mod_folder / "project_file" / f"w{PublishedFileId}.manifest"
            )

            (mo_mod_folder / "preview_file").mkdir(exist_ok=True)
            (mo_mod_folder / "project_file").mkdir(exist_ok=True)

            if txt_file.exists():
                txt_file.unlink()
            if log_file.exists():
                log_file.unlink()

            if preview_file.exists():
                preview_file.rename(
                    mo_mod_folder / "preview_file" / f"{PublishedFileId}.png"
                )

            if xml_file.exists():
                xml_file.rename(
                    mo_mod_folder / "project_file" / f"{PublishedFileId}.xml"
                )
                manifest_file.write_text(
                    self.workshop_items[PublishedFileId]["manifest"]
                )
        else:
            id = str(random.randint(1, 9999999))
            (source / f"l{id}.manifest").write_text("", encoding="utf-8")
            mo_mod_folder = dest
            preview_file = mo_mod_folder / "preview_icon.png"
            txt_file = mo_mod_folder / "modfiles.txt"
            xml_file = mo_mod_folder / "project.xml"
            log_file = mo_mod_folder / "steam_workshop_uploader.log"

            if log_file.exists():
                log_file.unlink()
            if txt_file.exists():
                txt_file.unlink()

            (mo_mod_folder / "preview_file").mkdir(exist_ok=True)
            if preview_file.exists():
                preview_file.rename(mo_mod_folder / "preview_file" / f"{id}.png")

            (mo_mod_folder / "project_file").mkdir(exist_ok=True)
            if xml_file.exists():
                xml_file.rename(xml_file.parent / "project_file" / f"{id}.xml")
                open(
                    xml_file.parent / "project_file" / f"l{id}.manifest",
                    "w+",
                    encoding="utf-8",
                ).write("")

    def init_data(self):
        data: list[list[str]] = []
        data = self.get_workshop_items()
        self.data = data
        self.model = MyTableModel(self.data)
        button_delegate = ButtonDelegate(
            self.handleButtonClicked, self.table_view
        )  # 创建按钮委托实例
        self.table_view.setItemDelegateForColumn(
            3, button_delegate
        )  # 在第一列使用按钮委托
        self.table_view.setModel(self.model)

    def displayName(self) -> str:
        return "暗黑地牢mod复制插件"

    def icon(self) -> QIcon:
        return QIcon()

    def tooltip(self) -> str:
        return "从创意工坊与游戏目录下mods文件夹复制mod"

    def author(self) -> str:
        return "LIC"

    def description(self) -> str:
        return "从创意工坊与游戏目录下mods文件夹复制mod"

    def name(self) -> str:
        return "暗黑地牢mod复制插件"

    def settings(self) -> Sequence[mobase.PluginSetting]:
        return [mobase.PluginSetting("key", "value", "default")]

    def version(self) -> mobase.VersionInfo:
        return mobase.VersionInfo(0, 0, 1)


def createPlugin():
    return DarkestDungeonModCopy()
