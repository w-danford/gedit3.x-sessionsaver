# For more info visit the article https://theawless.github.io/How-to-write-plugins-for-gedit/

# This file needs to be placed like ~/.local/share/gedit/plugins/example/__init__.py
# or renamed like ~/.local/share/gedit/plugins/example.py depending on .plugin file

import sys, subprocess, os, string
from gi.repository import GObject, Gedit, Gtk, Gio
from bs4 import BeautifulSoup



# text entry box, to save new session
# based on: https://python-gtk-3-tutorial.readthedocs.io/en/latest/entry.html
class SessionSaveWindow(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self, title="Session Name")
        self.set_size_request(400, 75)
        self.timeout_id = None

        vbox = Gtk.Box (orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.add (vbox)

        self.entry = Gtk.Entry()
        self.entry.set_text ("")
        vbox.pack_start (self.entry, True, True, 0)

        hbox = Gtk.Box (spacing=4)
        vbox.pack_start (hbox, True, True, 0)

        cancel = Gtk.Button.new_with_label ("Cancel")
        cancel.connect ("clicked", self.on_cancel_clicked)
        hbox.pack_start (cancel, True, True, 0)

        ok = Gtk.Button.new_with_label ("OK")
        ok.connect ("clicked", self.on_ok_clicked)
        hbox.pack_start (ok, True, True, 0)

        # vars required at init so to be visible in button callbacks
        self.file_list = []
        self.session_file = ""

    # activate window to create new, needed to pass variables
    def run_save (self, sess_file, this_list, app_window):
        # gobalize (to this class) passed vars
        self.file_list = this_list
        self.session_file = sess_file
        self.window = app_window
        # activate window
        self.show_all()
        self.set_modal(True)
        self.set_transient_for()
        # end: stays open waiting response


    # button action responces
    def on_cancel_clicked (self, button):
        ##print ('"Cancel" button was clicked')
        self.destroy()

    def on_ok_clicked (self, button):
        ##print ('"OK" button was clicked: %s' % self.entry.get_text())
        ses_name = self.entry.get_text()
        # consider that session name matches an existing one,
        # warn about this (so as not to create duplicate "session"s
        for c in self.session_file.find_all ("session"):
            if c['name'] == ses_name :
                ##print ("duplicate session name")
                dialog = Gtk.MessageDialog(
                               transient_for=self.window,
                               flags=0,
                               message_type=Gtk.MessageType.INFO,
                               buttons=Gtk.ButtonsType.OK,
                               text=("%s exists!" % ses_name),
                               secondary_text=("Choose another name or delete existing \"%s\"" % ses_name),)
                dialog.run()
                dialog.destroy()
                break
                self.destroy()

        # generate this new 'session' content
        files = (" <session name=\"%s\">\n" % (ses_name))
        for f in self.file_list:
            files += ("  <file path=\"%s\"/>\n" % f)
        files += (" </session>\n")
        ##print (files)

        # convert to BeautifulSoup 'file' (having this single tag)
        new_soup = BeautifulSoup (files, 'xml')
        # read back the newly generated tag
        new_tag = new_soup.find ("session")
        # get whole file, i.e 'saved-sessions' tag
        tag = self.session_file.find ("saved-sessions")
        # append new session
        tag.append (new_tag)
        ##print ("=== just tag:")
        ##print (tag)
        ##print ("=== final 'soup':")
        ##print (self.session_file)
        ##print (str (self.session_file))
        # save back to disk
        try:
            # Appears BeatifulSoup CANNOT write back, open in 'w' mode
            # BeatifulSoup only reads in an xml text, coverts to an xml editable object
            save_sessions = open (os.path.expanduser("~/.config/gedit/saved-sessions.xml"), mode='w')
        except OSError:
            # should not happen, 'w' mode truncates or forces creation
            print ("Could not open / update session file (%s)" %
                   os.path.expanduser("~/.config/gedit/saved-sessions.xml"))
        else:
            save_sessions.write (str(self.session_file))
        self.destroy()



# session select box, to open or delete an existing session
# based on: https://python-gtk-3-tutorial.readthedocs.io/en/latest/treeview.html
#           https://python-gtk-3-tutorial.readthedocs.io/en/latest/layout.html#listbox
class SessionSelectWindow(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self, title="Sessions")
        self.set_size_request(200, 200)
        self.timeout_id = None
        self.set_modal(True)
        self.set_transient_for()

        vbox = Gtk.Box (orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.add (vbox)

        self.list_view = Gtk.ListBox()
        self.list_view.set_selection_mode(Gtk.SelectionMode.SINGLE)
        vbox.pack_start (self.list_view, True, True, 0)

        self.set_border_width(10)


    # activate window to save, needed to pass variables
    def run_open (self, session_list, sessions, app_window):
        # action taken when clicking a row to open session
        def on_row_activated (listbox_widget, row):
            ##print (row.get_index(), session_list[row.get_index()])
            ses_name = session_list[row.get_index()]
            for c in sessions.find_all ("session"):
                # selected will be from those available
                if c['name'] == ses_name :
                    # open all files in this 'session'
                    for f in c.find_all ("file") :
                        open_file = Gio.File.parse_name (f['path'])
                        ##print (f)
                        ##print ("   ", f['path'])
                        app_window.create_tab_from_location (open_file, None, 0, 0, False, True)
                    break
            self.destroy()

        # create list of entries of saved session names
        ##print (session_list)
        for session_ref in session_list:
            row = Gtk.ListBoxRow()
            hbox = Gtk.Box (orientation=Gtk.Orientation.HORIZONTAL, spacing=50)
            row.add (hbox)
            label = Gtk.Label (label=session_ref, xalign=0)
            hbox.pack_start (label, True, True, 0)
            self.list_view.add (row)
            ##print (row.get_index(), session_ref)

        self.list_view.connect("row-activated", on_row_activated)
        self.show_all()
        # end: stays open waiting response


    # activate window to delete, needed to pass variables
    def run_delete (self, session_list, sessions):
        # action taken when clicking a row to open session
        def on_row_activated (listbox_widget, row):
            ##print (row.get_index(), session_list[row.get_index()])
            ses_name = session_list[row.get_index()]
            # loop through session_list, to .remove the selected ses_name
            for c in sessions.find_all ("session"):
                # selected will be from those available
                if c['name'] == ses_name :
                    session_list.remove (ses_name)
                    break

            ##print (session_list)
            # get whole file, i.e 'saved-sessions' tag
            tag = sessions.find ("saved-sessions")

            # process is create a new BeautifulSoup with empty 'saved-sessions' tag
            new_soup = BeautifulSoup ("<saved-sessions>\n</saved-sessions>", 'xml')
            new_tag = new_soup.find ("saved-sessions")
            ##print (str(new_tag))

            # loop through each of existing 'session' tags
            for c in sessions.find_all ("session"):
                # loop through (updated) session_list
                for n in session_list :
                    ##print (str(n))
                    # if this 'session' in list append to new 'saved-sessions' tag
                    if c['name'] == str(n) :
                        save_tag = c
                        ##print (str(save_tag))
                        new_tag.append (save_tag)
            ##print (new_soup)

            # save back to disk
            try:
                # Appears BeatifulSoup CANNOT write back, open in 'w' mode
                # BeatifulSoup only reads in an xml text, coverts to an xml editable object
                save_sessions = open (os.path.expanduser("~/.config/gedit/saved-sessions.xml"), mode='w')
            except OSError:
                # should not happen, 'w' mode truncates or forces creation
                print ("Could not open / update session file (%s)" %
                       os.path.expanduser("~/.config/gedit/saved-sessions.xml"))
            else:
                save_sessions.write (str(new_soup))
            self.destroy()

        # create list of entries of saved session names
        ##print (session_list)
        for session_ref in session_list:
            row = Gtk.ListBoxRow()
            hbox = Gtk.Box (orientation=Gtk.Orientation.HORIZONTAL, spacing=50)
            row.add (hbox)
            label = Gtk.Label (label=session_ref, xalign=0)
            hbox.pack_start (label, True, True, 0)
            self.list_view.add (row)
            ##print (row.get_index(), session_ref)

        self.list_view.connect("row-activated", on_row_activated)
        self.show_all()
        # end: stays open waiting response



# The following are the required API interface points
# Gedit.AppActivatable handles menu items to be added
# Gedit.WindowActivatable activates the menus and has their callbacks

# Provides do_activate(), do_deactivate()
class SessionAppActivatable(GObject.Object, Gedit.AppActivatable):
    app = GObject.property(type=Gedit.App)
    __gtype_name__ = "SessionAppActivatable"

    def __init__(self):
        GObject.Object.__init__(self)
        self.menu_ext = None
        self.menu_item = None


    def do_activate(self):
        self._build_menu()

    def _build_menu(self):
        # Get the extension from tools menu
        self.menu_ext = self.extend_menu("file-section")

        # These are items inserted in file menu.
        # Initially tried as a sub menu, "Sessions",
        #   but caused 'Segmentation fault (core dumped)',
        #   segfault: error 4 in libgio-2.0.so
        item = Gio.MenuItem.new("Open Session", 'win.open_session')
        self.menu_ext.append_menu_item(item)

        item = Gio.MenuItem.new("Save Session", 'win.save_session')
        self.menu_ext.append_menu_item(item)

        item = Gio.MenuItem.new("Delete Session", 'win.del_session')
        self.menu_ext.append_menu_item(item)


    def do_deactivate(self):
        self._remove_menu()

    def _remove_menu(self):
        # removing accelerator and destroying menu items
        self.app.set_accels_for_action("win.dictonator_start", ())
        self.menu_ext = None
        self.menu_item = None


# Provides do_activate(), do_deactivate(), do_update_state()
class SessionWindowActivatable(GObject.Object, Gedit.WindowActivatable):
    window = GObject.property(type=Gedit.Window)
    __gtype_name__ = "SessionWindowActivatable"

    def __init__(self):
        GObject.Object.__init__(self)


    # this is called every time the gui is updated
    def do_update_state(self):
        # if there is no document in sight, we disable the action, so we don't get NoneException
        if self.window.get_active_view() is not None:
            self.window.lookup_action('open_session').set_enabled(True)
            self.window.lookup_action('save_session').set_enabled(True)
            self.window.lookup_action('del_session').set_enabled(True)


    def do_activate(self):
        # Defining the action which was set earlier in AppActivatable.
        self._connect_menu()

    def _connect_menu(self):
        action_open = Gio.SimpleAction(name='open_session')
        action_open.connect('activate', self.open_session_cb)
        self.window.add_action(action_open)

        action_save = Gio.SimpleAction(name='save_session')
        action_save.connect('activate', self.save_session_cb)
        self.window.add_action(action_save)

        action_del = Gio.SimpleAction(name='del_session')
        action_del.connect('activate', self.del_session_cb)
        self.window.add_action(action_del)



    ### callback function for "open" ###
    def open_session_cb(self, action_open, data):
        try:
            sessions = BeautifulSoup (open(os.path.expanduser("~/.config/gedit/saved-sessions.xml")),'xml')
        except OSError:
            print ("Session file (%s) not found" %
                   os.path.expanduser("~/.config/gedit/saved-sessions.xml"))
            dialog = Gtk.MessageDialog(
                           transient_for=self.window,
                           flags=0,
                           message_type=Gtk.MessageType.INFO,
                           buttons=Gtk.ButtonsType.OK,
                           text="Could not open / update session file",)
            dialog.run()
            dialog.destroy()
        else:
            # build list of sessions saved
            session_list = []
            for c in sessions.find_all ("session"):
                this_name = c['name']
                ##print (this_name)
                session_list.append (this_name)
            # activate selection window
            session_popup = SessionSelectWindow()
            # run passing list of sessions and current gedit window
            session_popup.run_open (session_list, sessions, self.window)



    ### callback function for "save" ###
    def save_session_cb(self, action_save, data):
        try:
            sessions = BeautifulSoup (open(os.path.expanduser("~/.config/gedit/saved-sessions.xml")),'xml')
        except OSError:
            print ("Session file (%s) not found" %
                   os.path.expanduser("~/.config/gedit/saved-sessions.xml"))
            dialog = Gtk.MessageDialog(
                           transient_for=self.window,
                           flags=0,
                           message_type=Gtk.MessageType.INFO,
                           buttons=Gtk.ButtonsType.OK,
                           text="Could not open / update session file",)
            dialog.run()
            dialog.destroy()
        else:
            # get list of open files
            file_list = []
            for document in self.window.get_documents():
                gfile = document.get_location()
                if gfile:
                    file_list.append(gfile.get_uri())
            # activate session name dialog
            this_session = SessionSaveWindow()
            # run passing pointer to saved_sessions, generated file list
            # dialog: get session name
            this_session.run_save (sessions, file_list, self.window)



    ### callback function for "del" ###
    def del_session_cb(self, action_del, data):
        try:
            sessions = BeautifulSoup (open(os.path.expanduser("~/.config/gedit/saved-sessions.xml")),'xml')
        except OSError:
            print ("Session file (%s) not found" %
                   os.path.expanduser("~/.config/gedit/saved-sessions.xml"))
            dialog = Gtk.MessageDialog(
                           transient_for=self.window,
                           flags=0,
                           message_type=Gtk.MessageType.INFO,
                           buttons=Gtk.ButtonsType.OK,
                           text="Could not open / update session file",)
            dialog.run()
            dialog.destroy()
        else:
            # build list of sessions saved
            session_list = []
            for c in sessions.find_all ("session"):
                this_name = c['name']
                ##print (this_name)
                session_list.append (this_name)
            # activate selection window
            session_popup = SessionSelectWindow()
            # run passing list of sessions and current gedit window
            session_popup.run_delete (session_list, sessions)



    def do_deactivate(self):
        return
