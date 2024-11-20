import logging
import typing
from typing import Callable, Literal

from PyQt6.QtCore import (
    QAbstractItemModel,
    QAbstractTableModel,
    QEvent,
    QModelIndex,
    Qt,
)
from PyQt6.QtGui import QPainter
from PyQt6.QtWidgets import (
    QApplication,
    QStyle,
    QStyledItemDelegate,
    QStyleOptionButton,
    QStyleOptionViewItem,
    QWidget,
)

logger = logging.getLogger(__name__)


# 自定义数据模型类，继承自 QAbstractTableModel
class MyTableModel(QAbstractTableModel):
    def __init__(self, data: list[list[bool | str]]):
        super().__init__()
        self._data = data  # 存储表格数据

    def data(
        self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole
    ) -> Literal[Qt.CheckState.Checked, Qt.CheckState.Unchecked] | bool | str | None:
        if role == Qt.ItemDataRole.DisplayRole:
            # 返回显示角色的数据
            return self._data[index.row()][index.column()]
        elif (
            role == Qt.ItemDataRole.CheckStateRole and index.column() == 2
        ):  # 假设第二列有复选框
            # 返回复选框的状态
            value = self._data[index.row()][index.column()]
            return Qt.CheckState.Checked if value else Qt.CheckState.Unchecked
        return None

    def setData(
        self, index: QModelIndex, value: int, role: int = Qt.ItemDataRole.CheckStateRole
    ) -> bool:
        if role == Qt.ItemDataRole.CheckStateRole and index.column() == 2:
            # 设置复选框的状态
            self._data[index.row()][index.column()] = value == Qt.CheckState.Checked
            self.dataChanged.emit(index, index, [role])  # 发出数据改变信号
            return True
        return False

    def rowCount(self, parent: QModelIndex) -> int:  # type: ignore
        # 返回行数
        return len(self._data)

    def columnCount(self, parent: QModelIndex) -> int:  # type: ignore
        # 返回列数
        return len(self._data[0])

    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        if index.column() == 3:
            # 第二列包含可编辑的复选框
            return Qt.ItemFlag.ItemIsEnabled
        # 其他列是不可编辑的选择项
        return Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = 0):
        # 表头仅显示文本信息
        if role == Qt.ItemDataRole.DisplayRole:
            if orientation == Qt.Orientation.Horizontal:
                return ["mod 路径", "mod 名", "已存在", "-》", "mo2 名", "mo2 路径"][
                    section
                ]
            elif orientation == Qt.Orientation.Vertical:
                return str(section + 1)  # 假设行号从1开始


# 自定义委托类，用于在单元格中放置按钮


class ButtonDelegate(QStyledItemDelegate):
    def __init__(
        self,
        handleButtonClicked: Callable[[QModelIndex], None],
        parent: QWidget | None = None,
    ):
        self._parent = parent
        self.selected_index = None
        self._handleButtonClicked = handleButtonClicked
        super(ButtonDelegate, self).__init__(parent)

    def createEditor(
        self,
        parent: typing.Optional[QWidget],
        option: QStyleOptionViewItem,
        index: QModelIndex,
    ):
        return super().createEditor(parent, option, index)

    def setEditorData(self, editor: typing.Optional[QWidget], index: QModelIndex):
        if index.column() == 3:
            # 这里不需要设置数据，因为按钮没有数据
            pass
        else:
            super().setEditorData(editor, index)

    def setModelData(
        self,
        editor: typing.Optional[QWidget],
        model: typing.Optional[QAbstractItemModel],
        index: QModelIndex,
    ):
        if index.column() == 3:
            # 这里不需要将数据保存到模型中，因为按钮没有数据
            pass
        else:
            super().setModelData(editor, model, index)

    def paint(
        self,
        painter: typing.Optional[QPainter],
        option: QStyleOptionViewItem,
        index: QModelIndex,
    ):
        if index.column() == 3:
            opt = QStyleOptionButton()
            opt.rect = option.rect
            opt.text = "→"
            opt.state |= QStyle.StateFlag.State_Enabled
            if style := QApplication.style():
                style.drawControl(QStyle.ControlElement.CE_PushButton, opt, painter)
        else:
            super().paint(painter, option, index)

    def editorEvent(
        self,
        event: typing.Optional[QEvent],
        model: typing.Optional[QAbstractItemModel],
        option: QStyleOptionViewItem,
        index: QModelIndex,
    ):
        if (
            index.column() == 3
            and event
            and event.type() == QEvent.Type.MouseButtonRelease
        ):
            self._handleButtonClicked(index)
        return super().editorEvent(event, model, option, index)