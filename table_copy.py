import typing
from typing import Literal

from PyQt6.QtCore import (
    QAbstractItemModel,
    QAbstractTableModel,
    QEvent,
    QModelIndex,
    Qt,
)
from PyQt6.QtGui import QPainter
from PyQt6.QtWidgets import (
    QStyleOptionButton,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QStyle,
)


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
        if index.column() == 1:
            # 第二列包含可编辑的复选框
            return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsEnabled
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
    def paint(
        self,
        painter: typing.Optional[QPainter],
        option: QStyleOptionViewItem,
        index: QModelIndex,
    ):
        if not index.isValid():
            return super().paint(painter, option, index)

        if index.column() == 3:  # 假设按钮列是第二列
            # 创建一个按钮选项
            button_option = QStyleOptionButton()
            button_option.rect = option.rect
            button_option.text = "Click"
            button_option.state = (
                QStyle.StateFlag.State_Enabled | QStyle.StateFlag.State_Raised
            )

            # 使用样式绘制按钮
            style = option.widget.style()
            if style:
                style.drawControl(
                    QStyle.ControlElement.CE_PushButton,
                    button_option,
                    painter,
                    option.widget,
                )
        else:
            super().paint(painter, option, index)

    def editorEvent(
        self,
        event: typing.Optional[QEvent],
        model: typing.Optional[QAbstractItemModel],
        option: QStyleOptionViewItem,
        index: QModelIndex,
    ):
        if not index.isValid():
            return False
        if (
            event
            and index.column() == 3
            and event.type() == event.Type.MouseButtonRelease
        ):
            print(f"Button clicked for row {index.row()}")
            return True

        return super().editorEvent(event, model, option, index)


# class ButtonDelegate(QStyledItemDelegate):
#     def __init__(self, parent: QWidget | None = None):
#         super().__init__(parent)

#     def createEditor(
#         self,
#         parent: typing.Optional[QWidget],
#         option: QStyleOptionViewItem,
#         index: QModelIndex,
#     ) -> QWidget:
#         button = QPushButton("Click Me", parent)
#         button.clicked.connect(lambda: self.on_click(index))
#         return button

#     def setEditorData(
#         self, editor: typing.Optional[QWidget], index: QModelIndex
#     ) -> None:
#         pass

#     def setModelData(
#         self,
#         editor: typing.Optional[QWidget],
#         model: typing.Optional[QAbstractItemModel],
#         index: QModelIndex,
#     ) -> None:
#         pass

#     def updateEditorGeometry(
#         self,
#         editor: typing.Optional[QWidget],
#         option: QStyleOptionViewItem,
#         index: QModelIndex,
#     ) -> None:
#         if editor:
#             editor.setGeometry(option.rect)

#     def on_click(self, index: QModelIndex) -> None:
#         print(f"Button clicked at row {index.row()}, column {index.column()}")
