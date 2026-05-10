# -*- coding: utf-8 -*-
from .tasks import *
from .cli import main
try:
    from Plugins.Plugin import PluginDescriptor
    from Screens.ChoiceBox import ChoiceBox
except ImportError:
    PluginDescriptor = None
    ChoiceBox = None


def _run_selected_action(session, selection):
    if not selection: return
    choice = selection[1]
    if choice == 'channels': download_and_extract_channels()
    elif choice == 'backup': export_tuner_config()
    elif choice == 'tuner_a_auto': update_tuner_settings(tuner_target='0')
    elif choice == 'tuner_b_auto': update_tuner_settings(tuner_target='1')
    elif choice == 'astra': download_astra_conf()


def main_plugin(session, **kwargs):
    if ChoiceBox is None:
        main(); return
    choices = [
        ("Full Channel Update", 'channels'),
        ("Backup Tuner Configuration", 'backup'),
        ("Advanced Tuner Setup: A/Auto", 'tuner_a_auto'),
        ("Advanced Tuner Setup: B/Auto", 'tuner_b_auto'),
        ("Astra Configuration Update", 'astra'),
    ]
    session.openWithCallback(lambda selection: _run_selected_action(session, selection), ChoiceBox, title="Channel List & Tuner Settings Updater", list=choices)


def Plugins(**kwargs):
    if PluginDescriptor is None: return []
    return [PluginDescriptor(name="Channel List & Tuner Settings Updater", description="Channel list & tuner settings updater", where=[PluginDescriptor.WHERE_PLUGINMENU], fnc=main_plugin)]
