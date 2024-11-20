import logging
import re
from pathlib import Path
from typing import Sequence
from xml.etree import ElementTree as ET
from xml.etree.ElementTree import Element

import mobase
import vdf  # type: ignore
from PyQt6.QtCore import QModelIndex, Qt
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QInputDialog, QLineEdit, QMainWindow, QTableView, QWidget

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
        self.data: list[list[str | bool]] = []
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
        self.table_view.setColumnWidth(0, 550)
        self.table_view.setColumnWidth(1, 200)
        self.table_view.setColumnWidth(2, 10)
        self.table_view.setColumnWidth(3, 10)
        self.table_view.setColumnWidth(4, 200)
        self.table_view.setColumnWidth(5, 550)
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
            else:
                logger.debug(f"darkest_dungeon acf file not exist in {workshop_path}")
        mod_list = self._organizer.modList()
        mo_workshop_PublishedFileId: dict[str, mobase.IModInterface] = {
            str(i.stem.strip("w")): mod_list.getMod(str(i.parent.parent.name))
            for i in Path(self._organizer.modsPath()).glob("*/project_file/w*.manifest")
        }
        data: list[list[str | bool]] = []
        for game_workshop_path, workshop_items in workshop_path_workshop_items.items():
            for PublishedFileId in workshop_items.keys():
                if PublishedFileId in mo_workshop_PublishedFileId:
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
                            PublishedFileId in mo_workshop_PublishedFileId,
                            "",
                            ""
                            if PublishedFileId not in mo_workshop_PublishedFileId
                            else mo_workshop_PublishedFileId[PublishedFileId].name(),
                            ""
                            if PublishedFileId not in mo_workshop_PublishedFileId
                            else mo_workshop_PublishedFileId[
                                PublishedFileId
                            ].absolutePath(),
                        ]
                    )
        return data

    def handleButtonClicked(self, index: QModelIndex):
        input = QInputDialog(self.__parentWidget, Qt.WindowType.Dialog)
        text, ok = QInputDialog.getText(
            self.__parentWidget,
            "QInputDialog.getText()",
            "User name:",
            QLineEdit.EchoMode.Normal,
            "",
        )
        input.show()
        if ok:
            logger.info(text)

    def init_data(self):
        data: list[list[str | bool]] = []
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
