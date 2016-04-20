from fireworks import Firework, Workflow, LaunchPad
from matmethods.vasp.firetasks.glue_tasks import PassCalcLocs, CopyVaspOutputs
from matmethods.vasp.firetasks.parse_outputs import VaspToDbTask
from matmethods.vasp.firetasks.run_calc import RunVaspDirect
from matmethods.vasp.firetasks.write_inputs import WriteVaspFromIOSet, \
    WriteVaspStaticFromPrev, WriteVaspNSCFFromPrev
from matmethods.vasp.input_sets import StructureOptimizationVaspInputSet
from matmethods.vasp.vasp_powerups import use_custodian, decorate_write_name
from matmethods.vasp.workflows.base.single_vasp import get_wf_single_Vasp
from pymatgen import Lattice, IStructure

__author__ = 'Anubhav Jain, Kiran Mathew'
__email__ = 'ajain@lbl.gov, kmathew@lbl.gov'


def get_wf_bandstructure_Vasp(structure, vasp_input_set=None, vasp_cmd="vasp",
                              db_file=None):
    """
    Return vasp workflow consisting of 4 fireworks.
    Firework 1 : write vasp input set for structural relaxation, run vasp,
        pass run location and database insertion.
    Firework 2 : copy files from previous run, write vasp input set for
        static run, run vasp, pass run location and database insertion.
    Firework 3 : copy files from previous run, write vasp input set for
        non self-consistent(constant charge density) run in uniform mode,
        run vasp, pass run location and database insertion.
    Firework 4 : copy files from previous run, write vasp input set for
        non self-consistent(constant charge density) run in line mode,
        run vasp, pass run location and database insertion.

    Args:
        structure (Structure): input structure to be relaxed.
        vasp_input_set (DictVaspInputSet): vasp input set.
        vasp_cmd (str): command to run
        db_file (str): path to file containing the database credentials.

    Returns:
        Workflow
     """
    vasp_input_set = vasp_input_set if vasp_input_set else StructureOptimizationVaspInputSet()

    task_label = "structure optimization"
    t1 = []
    t1.append(WriteVaspFromIOSet(structure=structure, vasp_input_set=vasp_input_set))
    t1.append(RunVaspDirect(vasp_cmd=vasp_cmd))
    t1.append(PassCalcLocs(name=task_label))
    t1.append(VaspToDbTask(db_file=db_file,
                           additional_fields={"task_label": task_label}))
    fw1 = Firework(t1, name="{}-{}".format(structure.composition.reduced_formula, task_label))

    task_label = "static"
    t2 = []
    t2.append(CopyVaspOutputs(calc_loc=True))
    t2.append(WriteVaspStaticFromPrev())
    t2.append(RunVaspDirect(vasp_cmd=vasp_cmd))
    t2.append(PassCalcLocs(name=task_label))
    t2.append(VaspToDbTask(db_file=db_file, additional_fields={"task_label": task_label}))
    fw2 = Firework(t2, parents=fw1, name="{}-{}".format(structure.composition.reduced_formula,
                                                        task_label))

    task_label = "nscf uniform"
    t3 = []
    t3.append(CopyVaspOutputs(calc_loc=True, additional_files=["CHGCAR"]))
    t3.append(WriteVaspNSCFFromPrev(mode="uniform"))
    t3.append(RunVaspDirect(vasp_cmd=vasp_cmd))
    t3.append(PassCalcLocs(name=task_label))
    t3.append(VaspToDbTask(db_file=db_file,
                           additional_fields={"task_label": task_label},
                           parse_dos=True, bandstructure_mode="uniform"))
    fw3 = Firework(t3, parents=fw2, name="{}-{}".format(structure.composition.reduced_formula,
                                                        task_label))

    # line mode (run in parallel to uniform)
    t4 = []
    task_label = "nscf line"
    t4.append(CopyVaspOutputs(calc_loc=True, additional_files=["CHGCAR"]))
    t4.append(WriteVaspNSCFFromPrev(mode="line"))
    t4.append(RunVaspDirect(vasp_cmd=vasp_cmd))
    t4.append(PassCalcLocs(name=task_label))
    t4.append(VaspToDbTask(db_file=db_file, additional_fields={"task_label": task_label},
                           bandstructure_mode="line"))
    fw4 = Firework(t4, parents=fw2, name="{}-{}".format(structure.composition.reduced_formula,
                                                        task_label))

    return Workflow([fw1, fw2, fw3, fw4], name=structure.composition.reduced_formula)


def add_to_lpad(workflow, decorate=False):
    """
    Add the workflow to the launchpad

    Args:
        workflow (Workflow): workflow for db insertion
        decorate (bool): If set an empty file with the name
            "FW--<fw.name>" will be written to the launch directory
    """
    lp = LaunchPad.auto_load()
    workflow = decorate_write_name(workflow) if decorate else workflow
    lp.add_wf(workflow)


if __name__ == "__main__":
    coords = [[0, 0, 0], [0.75, 0.5, 0.75]]
    lattice = Lattice([[3.8401979337, 0.00, 0.00],
                       [1.9200989668, 3.3257101909, 0.00],
                       [0.00, -2.2171384943, 3.1355090603]])
    structure = IStructure(lattice, ["Si"] * 2, coords)
    wf = get_wf_single_Vasp(structure)
    add_to_lpad(wf, decorate=True)