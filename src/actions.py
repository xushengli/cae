#!/usr/bin/env python3
# -*- coding: utf-8 -*-

""" © Ihor Mirzov, May 2020
Distributed under GNU General Public License v3.0

Main window actions - all processed signals. """

from PyQt5 import QtWidgets
import cae
import gui


"""
s - Settings
w - Window
m - Model
t - Tree
j - Job
"""
def actions(s, w, m, t, j):
    w.keyPressEvent = t.keyPressEvent

    # File actions
    w.action_file_import.triggered.connect(lambda: cae.import_file(s, w, m, t, j))
    w.action_file_settings.triggered.connect(s.open)
    w.action_file_exit.triggered.connect(QtWidgets.qApp.quit)

    # Job actions
    w.action_job_paint_elsets.triggered.connect(
        lambda: gui.cgx.paint_elsets(w, m))
    w.action_job_paint_surfaces.triggered.connect(
        lambda: gui.cgx.paint_surfaces(w, m))
    w.action_job_write_input.triggered.connect(
        lambda: j.write_input(m.KOM.get_INP_code_as_lines()))
    w.action_job_write_input.triggered.connect(
        lambda: w.setWindowTitle('CalculiX CAE - ' + j.name))
    w.action_job_edit_inp.triggered.connect(lambda: j.edit_inp(s))
    w.action_job_subroutine.triggered.connect(lambda: j.open_subroutine(s))
    w.action_job_rebuild_ccx.triggered.connect(lambda: j.rebuild_ccx(s))
    w.action_job_submit.triggered.connect(lambda: j.submit(s))
    w.action_job_view_log.triggered.connect(lambda: j.view_log(s))
    w.action_job_cgx_inp.triggered.connect(lambda: j.cgx_inp(s, w))
    w.action_job_cgx_frd.triggered.connect(lambda: j.cgx_frd(s, w))
    w.action_job_export_vtu.triggered.connect(j.export_vtu)
    w.action_job_paraview.triggered.connect(lambda: j.open_paraview(s))

    # Help actions
    w.action_help_readme.triggered.connect(
        lambda: w.help('https://github.com/calculix/cae#calculix-cae'))
    w.action_help_examples.triggered.connect(
        lambda: w.help('https://github.com/calculix/examples'))
    w.action_help_issues.triggered.connect(
        lambda: w.help('https://github.com/calculix/cae/issues'))

    # treeView actions
    w.treeView.doubleClicked.connect(t.doubleClicked)
    w.treeView.clicked.connect(t.clicked)
    w.treeView.customContextMenuRequested.connect(t.rightClicked)
    w.treeView.expanded.connect(t.treeViewExpanded)
    w.treeView.collapsed.connect(t.treeViewCollapsed)

    # ToolBar actions
    w.action_view_minus_x.triggered.connect(lambda: w.post('rot -x'))
    w.action_view_minus_y.triggered.connect(lambda: w.post('rot -y'))
    w.action_view_minus_z.triggered.connect(lambda: w.post('rot -z'))
    w.action_view_plus_x.triggered.connect(lambda: w.post('rot x'))
    w.action_view_plus_y.triggered.connect(lambda: w.post('rot y'))
    w.action_view_plus_z.triggered.connect(lambda: w.post('rot z'))
    w.action_view_frame.triggered.connect(lambda: w.post('frame'))

    w.action_view_iso.triggered.connect(lambda: w.post('rot -z'))
    w.action_view_iso.triggered.connect(lambda: w.post('rot r 45'))
    w.action_view_iso.triggered.connect(lambda: w.post('rot u 45'))

    w.action_view_line.triggered.connect(lambda: w.post('view elem off'))
    w.action_view_line.triggered.connect(lambda: w.post('view line'))
    w.action_view_fill.triggered.connect(lambda: w.post('view elem off'))
    w.action_view_fill.triggered.connect(lambda: w.post('view fill'))
    w.action_view_elem.triggered.connect(lambda: w.post('view fill'))
    w.action_view_elem.triggered.connect(lambda: w.post('view elem'))
