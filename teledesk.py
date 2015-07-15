# encoding: utf-8
from PyQt4 import QtGui, QtCore
import main_window
import item_edit_dialog
import new_folder_dialog
import os
from data_storage import DataStorage
from serializer import Serializer
import win32crypt
import binascii
import time


class MyWindow(QtGui.QWidget):

    #datastorage root element id
    ROOT_ELEMENT_ID = "1"

    """ UI class"""
    def __init__(self, parent=None):

        super(MyWindow, self).__init__()
        #list of data sources
        self.sources = []
        source1 = {"Name": "Local_storage", "Type": "local", "Path": "config.db"}
        source2 = {"Name": "Common_storage", "Type": "common", "Path": "config2.db"}

        self.sources.append(source1)
        self.sources.append(source2)


        self.ds = DataStorage(self.sources)

        # GUI
        QtGui.QWidget.__init__(self, parent)
        self.ui = main_window.Ui_MainWindow()
        self.ui.setupUi(self)

        #tree view
        model = QtGui.QStandardItemModel()
        model.setHorizontalHeaderLabels(['Name'])
        self.ui.treeView.setModel(model)
        self.ui.treeView.setColumnHidden(1, True)
        self.ui.treeView.header().close()

        for stor in self.sources:
            root = QtGui.QStandardItem(stor["Name"])
            self.fill_tree(stor["Name"], self.ROOT_ELEMENT_ID, root)
            model.appendRow(root)
            self.ui.treeView.expand(model.indexFromItem(root))


        self.ui.treeView.doubleClicked.connect(self.init_connection)
        self.ui.treeView.clicked.connect(self.display_item_info)
        self.ui.deleteGroupAction.triggered.connect(self.remove_item)
        self.ui.editServerAction.triggered.connect(self.edit_item)
        self.ui.addGroupAction.triggered.connect(self.add_new_folder)
        self.ui.addServerAction.triggered.connect(self.add_new_item)
        self.ui.removeServerAction.triggered.connect(self.remove_item)

        
        #Minimizing to tray
        style = self.style()
        # Set the window and tray icon to something
        icon = style.standardIcon(QtGui.QStyle.SP_ComputerIcon)
        self.tray_icon = QtGui.QSystemTrayIcon()
        self.tray_icon.setIcon(QtGui.QIcon(icon))
        self.setWindowIcon(QtGui.QIcon(icon))




        # Restore the window when the tray icon is double clicked.
        self.tray_icon.activated.connect(self.restore_window_from_tray)

    
    def event(self, event):    
        if (event.type() == QtCore.QEvent.WindowStateChange and 
                self.isMinimized()):
            self.setWindowFlags(self.windowFlags() & ~QtCore.Qt.Tool)
            self.tray_icon.show()
            return True
        else: 
            return super(MyWindow, self).event(event)
    """
    def closeEvent(self, event):
        reply = QtGui.QMessageBox.question(self, 'Message', "Are you sure to quit?",
            QtGui.QMessageBox.Yes | QtGui.QMessageBox.No,
            QtGui.QMessageBox.No)

        if reply == QtGui.QMessageBox.Yes:
            event.accept()
        else:
            self.tray_icon.show()
            self.hide()
            event.ignore()
    """
    def keyPressEvent(self, event):

        #DEL key
        if event.key() == 16777223:
            self.remove_item()

        #INS key
        elif event.key() == 16777222:
            self.add_new_item()

    def restore_window_from_menu(self):
        self.tray_icon.hide()
        self.showNormal()

    def restore_window_from_tray(self, reason):
        if reason == QtGui.QSystemTrayIcon.DoubleClick:
            self.tray_icon.hide()
            self.showNormal()

        if reason == QtGui.QSystemTrayIcon.Trigger:
            tray_menu = QtGui.QMenu(None)

            self.tray_icon.setContextMenu(tray_menu)
            self.tray_icon.setToolTip("TeleDesk")

            #self.ui.exitAction.triggered.connect(QtGui.qApp.quit)
            #self.ui.exitAction = QtGui.QAction('&Exit', MyWindow)

            #Title
            self.ui.restore_win = QtGui.QAction("&TeleDesk", self)
            tray_menu.addAction(self.ui.restore_win)
            self.ui.restore_win.triggered.connect(self.restore_window_from_menu)

            tray_menu.addSeparator()

            folder_icon = QtGui.QIcon("res/folder.png")
            computer_icon = QtGui.QIcon("res/computer.png")

            for stor in self.sources:
                top_list = self.ds.get_rated_items(stor["Name"], 32)
                node_entry = tray_menu.addAction(stor["Name"])
                node_entry.setIcon(folder_icon)
                if top_list.__len__():
                    for menu_item in top_list:
                        entry = tray_menu.addAction(str(menu_item["NAME"]))
                        entry.setIcon(computer_icon)
                        self.connect(entry, QtCore.SIGNAL('triggered()'),
                                     lambda menu_item = menu_item: self.prn( stor["Name"], str(menu_item["ID"]), str(menu_item["NAME"])))

            tray_menu.addSeparator()

            #Exit
            self.ui.extact = QtGui.QAction("&Exit", self)
            tray_menu.addAction(self.ui.extact)
            self.ui.extact.triggered.connect(QtGui.qApp.quit)

            self.tray_icon.contextMenu().popup(QtGui.QCursor.pos())



    def prn(self, storage_name, selected_id, selected_name):
        self.ds.update_item_rating(storage_name, selected_id)
        item = self.ds.get_profile_info(storage_name, selected_id)
        if item.__len__():
            te = Serializer().serialize_to_file_win_rdp(item[0], "7.1", selected_name+".rdp")
            if te:
                os.system(selected_name+".rdp")
                time.sleep(3)
                os.remove(selected_name+".rdp")
        
    def fill_tree(self, storage, parent, root):
        cildlist = self.ds.get_folders_children(storage, parent)

        for chld in cildlist:
            child_node = QtGui.QStandardItem(str(chld["NAME"]))
            child_node.setData(QtCore.QVariant(str(chld["ID"])))

            #icon = QtGui.QIcon()
            if str(chld["PROFILE"]) == u'':
                icon = QtGui.QIcon("res/folder.png")
            elif str(chld["PROFILE"]):
                icon = QtGui.QIcon("res/computer.png")
            else:
                pass

            child_node.setIcon(icon)
            root.appendRow(child_node)
            self.ui.treeView.expand(self.ui.treeView.model().indexFromItem(child_node))

            self.fill_tree(storage, str(chld["ID"]), child_node)

    def update_tree(self):

        model = QtGui.QStandardItemModel()
        model.setHorizontalHeaderLabels(['Name'])
        self.ui.treeView.setModel(model)
        for stor in self.sources:
            root = QtGui.QStandardItem(stor["Name"])
            self.fill_tree(stor["Name"], self.ROOT_ELEMENT_ID , root)
            model.appendRow(root)
            self.ui.treeView.expand(model.indexFromItem(root))

    def display_item_info(self, index):
        selected_id = str(index.model().itemFromIndex(index).data().toString())
        storage_name = self.get_storage_name(index)

        if selected_id:
            item = self.ds.get_profile_info(storage_name, selected_id)

            if item.__len__():
                alias = str(item[0]["ALIAS"])
                server = str(item[0]["SERVER"])
                port = str(item[0]["PORT"])
                user = str(item[0]["USER"])
                self.ui.textEditDescription.setText("Name - " + alias + "\n"
                                                    + "Server - " + server + "\n"
                                                    + "Port - " + port + "\n"
                                                    + "User - " + user + "\n")
            else:
                self.ui.textEditDescription.setText("")

    def init_connection(self, index):
        selected_id = str(index.model().itemFromIndex(index).data().toString())
        selected_name = str(index.model().itemFromIndex(index).text())
        storage_name = self.get_storage_name(index)

        self.ds.update_item_rating(storage_name, selected_id)
        item = self.ds.get_profile_info(storage_name, selected_id)
        if item.__len__():
            te = Serializer().serialize_to_file_win_rdp(item[0], "7.1", selected_name+".rdp")
            if te:
                os.system(selected_name+".rdp")
                time.sleep(3)
                os.remove(selected_name+".rdp")

    def edit_item(self):
        index = self.ui.treeView.selectedIndexes()[0]
        selected_id = str(index.model().itemFromIndex(index).data().toString())
        storage_name = self.get_storage_name(index)

        item = self.ds.get_profile_info(storage_name, selected_id)
        if item.__len__():
            item_data = {"Storage": storage_name, "Parent": None, "ItemData": item[0], "Mode": "Edit"}
            input_dialog = ItemEditDialog(self.ds, item_data)
            input_dialog.ui.pushButtonClose.clicked.connect(lambda: input_dialog.close())
            input_dialog.exec_()
            if input_dialog.updated:
                self.update_tree()

    def add_new_item(self):
        index = self.ui.treeView.selectedIndexes()[0]
        selected_name = str(index.model().itemFromIndex(index).text())
        storage_name = str(index.model().itemFromIndex(index).parent().text())
        item = self.ds.get_folder_id(storage_name, selected_name)

        if item.__len__():
            item_data = {"Storage": storage_name, "Parent": str(item[0]["ID"]), "ItemData": None, "Mode": "AddItem"}
            input_dialog = ItemEditDialog(self.ds, item_data)
            input_dialog.exec_()
            if input_dialog.updated:
                self.update_tree()

    def add_new_folder(self):
        index = self.ui.treeView.selectedIndexes()[0]
        selected_name = str(index.model().itemFromIndex(index).text())
        storage_name = str(index.model().itemFromIndex(index).text())

        item = self.ds.get_folder_id(storage_name, selected_name)
        if item.__len__():
            item_data = {"Storage": storage_name, "Parent": str(item[0]["ID"]), "ItemData": None, "Mode": "AddFolder"}
            inputter = NewFolderDialog(self.ds, item_data)
            inputter.exec_()
            if inputter.updated:
                self.update_tree()

    def remove_item(self):
        index = self.ui.treeView.selectedIndexes()[0]
        selected_id = str(index.model().itemFromIndex(index).data().toString())
        storage_name = self.get_storage_name(index)
        if selected_id != self.ROOT_ELEMENT_ID:
            #if there are child elements, asking user before deleting
            child_elements = self.ds.get_child_elements(storage_name, selected_id)
            if child_elements.__len__():
                reply = QtGui.QMessageBox.question(self, 'Message', "Delete element with all child elements?",
                QtGui.QMessageBox.Yes | QtGui.QMessageBox.No,
                QtGui.QMessageBox.No)
                if reply == QtGui.QMessageBox.Yes:
                    self.ds.delete_folder(storage_name, selected_id)
            else:
                reply = QtGui.QMessageBox.question(self, 'Message', "Delete element?",
                QtGui.QMessageBox.Yes | QtGui.QMessageBox.No,
                QtGui.QMessageBox.No)
                if reply == QtGui.QMessageBox.Yes:
                    self.ds.delete_folder(storage_name, selected_id)

            self.update_tree()

    @staticmethod
    def get_storage_name(index):

        item = index.model().itemFromIndex(index)
        storage_name = str(item.text())
        while item:
            if not item.parent():
                storage_name = str(item.text())
            item = item.parent()
        return storage_name


class ItemEditDialog(QtGui.QDialog):

    def __init__(self, ds, item_data=None):
        self.ds = ds
        self.storage_name = item_data["Storage"]
        self.updated = False
        self.parent = item_data["Parent"]
        QtGui.QWidget.__init__(self, None)
        self.ui = item_edit_dialog.Ui_EditWin()
        self.ui.setupUi(self)
        if item_data["Mode"] == "Edit":
            self.item_to_edit = item_data["ItemData"]["ID"]
            self.ui.lineEditName.setText(item_data["ItemData"]["ALIAS"])
            self.ui.lineEditServer.setText(item_data["ItemData"]["SERVER"])
            self.ui.lineEditPort.setText(item_data["ItemData"]["PORT"])
            self.ui.lineEditUser.setText(item_data["ItemData"]["USER"])
            self.ui.lineEditDomain.setText(item_data["ItemData"]["DOMAIN"])
            self.ui.pushButtonSave.clicked.connect(self.edit_item)
        elif item_data["Mode"] == "AddItem":
            #self.ui.lineEditName.setText(item_data["Parent"])
            self.ui.pushButtonSave.clicked.connect(self.create_new_item)
        else:
            pass

    def create_new_item(self):
        name = str(self.ui.lineEditName.text())
        server = str(self.ui.lineEditServer.text())
        domain = str(self.ui.lineEditDomain.text())
        user = str(self.ui.lineEditUser.text())
        port = str(self.ui.lineEditPort.text())

        pwdHash = win32crypt.CryptProtectData(str(self.ui.lineEditPassword.text()), u'psw', None, None, None, 0)
        password = binascii.hexlify(pwdHash)

        self.ds.create_new_profile(self.storage_name, name, server, domain, port, user, password)

        item = self.ds.get_profile_id(self.storage_name, name)
        if item.__len__():
            id = str(item[0]["ID"])
            self.ds.create_new_profile_folder(self.storage_name, self.parent, name, id)
            self.updated = True
            self.close()

    def edit_item(self):
        name = str(self.ui.lineEditName.text())
        server = str(self.ui.lineEditServer.text())
        domain = str(self.ui.lineEditDomain.text())
        user = str(self.ui.lineEditUser.text())
        port = str(self.ui.lineEditPort.text())
        password = unicode(self.ui.lineEditPassword.text())

        if password != u'':
            pwdHash = win32crypt.CryptProtectData(password, u'psw', None, None, None, 0)
            password = binascii.hexlify(pwdHash)
        else:
            password = u''

        self.ds.update_profile(self.storage_name, self.item_to_edit,  name, server, domain,  port, user, password)
        self.close()


class NewFolderDialog(QtGui.QDialog):

    def __init__(self, ds, item_data=None):
        self.updated = False
        self.ds = ds
        self.storage = item_data["Storage"]
        self.parent = item_data["Parent"]
        QtGui.QWidget.__init__(self, None)
        self.ui = new_folder_dialog.Ui_NewFolderWin()
        self.ui.setupUi(self)
        self.ui.pushButtonOk.clicked.connect(self.ok)
        self.ui.pushButtonCancel.clicked.connect(self.cancel)
        self.ui.labelParentName.setText("Enter folder name")

    def ok(self):
        name = str(self.ui.lineEditFolderName.text())
        self.ds.create_new_folder(self.storage, self.parent, name)
        self.updated = True
        self.close()

    def cancel(self):
        self.close()


if __name__ == "__main__":
    import sys
    app = QtGui.QApplication(sys.argv)
    window = MyWindow()
    window.move(app.desktop().screen().rect().center() - window.rect().center())
    window.show()
    sys.exit(app.exec_())


