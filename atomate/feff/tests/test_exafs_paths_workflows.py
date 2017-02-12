# coding: utf-8

from __future__ import division, print_function, unicode_literals, absolute_import

import os
import shutil
import unittest
from glob import glob

from pymatgen import Structure
from pymatgen.io.feff.inputs import Paths
from pymatgen.io.feff.sets import MPEXAFSSet

from fireworks.core.launchpad import LaunchPad

from atomate.feff.workflows.xas import get_wf_exafs_paths
from atomate.feff.firetasks.glue_tasks import CopyFeffOutputs
from atomate.feff.firetasks.write_inputs import WriteEXAFSPaths
from atomate.feff.fireworks.core import EXAFSPathsFW

__author__ = 'Kiran Mathew'
__email__ = 'kmathew@lbl.gov'

module_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)))
db_dir = os.path.join(module_dir, "..", "..", "common", "reference_files", "db_connections")


class TestEXAFSPaths(unittest.TestCase):

    def setUp(self):
        self.struct = Structure.from_file(os.path.join(module_dir, "reference_files", "feo_781777.json"))
        self.scratch_dir = os.path.join(module_dir, "scratch")
        if os.path.exists(self.scratch_dir):
            shutil.rmtree(self.scratch_dir)
        os.makedirs(self.scratch_dir)
        os.chdir(self.scratch_dir)

    def test_copy_feff_outputs_task(self):
        t = CopyFeffOutputs(calc_dir=os.path.join(module_dir, "reference_files"))
        t.run_task({})
        ans = ["Co2O2.cif", "feff_eels.inp", "feo_781777.json"]
        files = glob("*")
        self.assertEqual(sorted(ans), sorted(files))

    def test_write_paths_task(self):
        exafs = MPEXAFSSet(0, self.struct, edge='K', radius=10)
        t = WriteEXAFSPaths(feff_input_set=exafs, paths=[[249 , 0], [85, 0]])
        paths = Paths(exafs.atoms, [[249, 0], [85, 0]])
        paths.write_file("paths_ans.dat")
        t.run_task({})
        with open("paths_ans.dat", "r") as ans, open("paths.dat", "r") as tmp:
            self.assertEqual(ans.readlines(), tmp.readlines())

    def test_exafs_paths_fw(self):
        fw = EXAFSPathsFW(0, self.struct, [[249 , 0], [85, 0]])
        fw_dict = fw.as_dict()
        self.assertEqual(len(fw_dict["spec"]["_tasks"]), 5)
        ans = ['{{atomate.feff.firetasks.glue_tasks.CopyFeffOutputs}}',
               '{{atomate.feff.firetasks.write_inputs.WriteFeffFromIOSet}}',
               '{{atomate.feff.firetasks.write_inputs.WriteEXAFSPaths}}',
               '{{atomate.feff.firetasks.run_calc.RunFeffDirect}}',
               '{{atomate.feff.firetasks.parse_outputs.AddPathsToFilepadTask}}']
        self.assertEqual(ans, [ft["_fw_name"] for ft in fw_dict["spec"]["_tasks"]])

    def test_exafs_paths_wflow(self):
        wflow = get_wf_exafs_paths(0, self.struct, [[249, 0], [85, 0]], feff_cmd="feff", db_file=None)
        wf_dict = wflow.as_dict()
        self.assertEqual(len(wf_dict["fws"]), 2)
        ans = ['FeO-EXAFS-K-0', 'FeO-EXAFS Paths']
        self.assertEqual(ans, [ft["name"] for ft in wf_dict["fws"]])

    def tearDown(self):
        shutil.rmtree(self.scratch_dir)


if __name__ == "__main__":
    unittest.main()
