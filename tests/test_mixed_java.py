import os

import angr
from angr.state_plugins.javavm_memory import SimJavaVmMemory
from angr.state_plugins.keyvalue_memory import SimKeyValueMemory
from angr.state_plugins.symbolic_memory import SimSymbolicMemory
from archinfo.arch_amd64 import ArchAMD64
from archinfo.arch_soot import (ArchSoot, SootAddressDescriptor,
                                SootMethodDescriptor)

test_location = str(os.path.join(os.path.dirname(
    os.path.realpath(__file__)), "..", "..", "binaries", "tests"))

#
# Loading
#

def test_loading_of_native_libs_with_ld_path(binary_dir="1"):
    native_libs_ld_path = os.path.join(
        test_location, "mixed_java", binary_dir, "libs"
    )
    jar_path = os.path.join(
        test_location, "mixed_java", binary_dir, "MixedJava.jar"
    )
    # define which libraries to load (+ the load path)
    jni_options = {
        'native_libs': ['libmixedjava.so'],
        'native_libs_ld_path': native_libs_ld_path
    }
    project = angr.Project(jar_path, main_opts=jni_options)
    # check if libmixedjava.so was loaded
    loaded_libs = [lib.provides for lib in project.loader.all_elf_objects]
    assert 'libmixedjava.so' in loaded_libs

def test_loading_of_native_libs_without_ld_path(binary_dir="2"):
    # the folder of the JAR is implicitly used as an additional load path
    project = create_project(binary_dir)
    # check if libmixedjava.so was loaded
    loaded_libs = [lib.provides for lib in project.loader.all_elf_objects]
    assert 'libmixedjava.so' in loaded_libs

#
# SimStates
#

def test_toggling_of_simstate(binary_dir="2"):
    project = create_project(binary_dir)

    state = project.factory.entry_state()
    assert state.javavm_with_jni
    assert state.javavm
    assert state.ip_is_soot_addr
    assert isinstance(state.arch, ArchSoot)
    assert isinstance(state.memory, SimJavaVmMemory)
    assert isinstance(state.registers, SimKeyValueMemory)

    state.regs.ip = 1
    assert not state.ip_is_soot_addr
    assert isinstance(state.arch, ArchAMD64)
    assert isinstance(state.memory, SimSymbolicMemory)
    assert isinstance(state.registers, SimSymbolicMemory)

    state.regs._ip = project.entry

    assert state.ip_is_soot_addr
    assert isinstance(state.arch, ArchSoot)
    assert isinstance(state.memory, SimJavaVmMemory)
    assert isinstance(state.registers, SimKeyValueMemory)

    state.ip = 1
    assert not state.ip_is_soot_addr
    assert isinstance(state.arch, ArchAMD64)
    assert isinstance(state.memory, SimSymbolicMemory)
    assert isinstance(state.registers, SimSymbolicMemory)

    state_copy = state.copy()
    assert not state_copy.ip_is_soot_addr
    assert isinstance(state_copy.arch, ArchAMD64)
    assert isinstance(state_copy.memory, SimSymbolicMemory)
    assert isinstance(state_copy.registers, SimSymbolicMemory)

#
# JNI Interface
#

def test_jni_env_get_version(binary_dir="2"):
    project = create_project(binary_dir)
    end_state = get_last_state_of_method(project, "MixedJava.main")
    # check return value
    jni_version_1_8 = 0x10008
    assert_values(end_state, {'i0': jni_version_1_8})

#
# Datatypes
#

def test_primitive_types(binary_dir="3"):
    project = create_project(binary_dir)
    # boolean
    values = {'z0': 1, 'z1': 0, 'z2': 1, 'z3': 0, 'z4': 1}
    end_state = get_last_state_of_method(project, "MixedJava.test_boolean")
    assert_values(end_state, values)
    # byte
    values = {'b5': 30, 'b8': 0xffffff80, 'b11': 0}
    end_state = get_last_state_of_method(project, "MixedJava.test_byte")
    assert_values(end_state, values)
    # char
    values = {'c4': 21, 'c6': 0, 'c9': 1}
    end_state = get_last_state_of_method(project, "MixedJava.test_char")
    assert_values(end_state, values)
    # short
    values = {'s3': 0x1000, 's0': 11, 's5': 0xfffff000, 's9': 0}
    end_state = get_last_state_of_method(project, "MixedJava.test_short")
    assert_values(end_state, values)
    # int
    values = {'i1': 0xfffffff6, 'i3': 0, 'i5': 0x80000001, 'i7': 0x7fffffff}
    end_state = get_last_state_of_method(project, "MixedJava.test_int")
    assert_values(end_state, values)
    # long
    values = {'l1': 0xffffffffffffffff, 'l3': 1}
    end_state = get_last_state_of_method(project, "MixedJava.test_long")
    assert_values(end_state, values)

#
# JNI Array Functions
#

def test_jni_newarray(binary_dir="4"):
    end_state = get_last_state_of_method(project=create_project(binary_dir),
                                         method_fullname="MixedJava.test_jni_newarray")
    values =  { 'i0':0, 'i1':1, 'i2':2, 'i3':3, 'i4':4 }
    assert_values(end_state, values)

def test_jni_getarrayregion(binary_dir="4"):
    end_state = get_last_state_of_method(project=create_project(binary_dir),
                                         method_fullname="MixedJava.test_jni_getarrayregion")
    # constrain a to 15
    a = load_value_from_stack(end_state, 'i1')
    end_state.state.solver.add(a == 15)
    # only solution is 7+8=15
    idx = end_state.posix.stdin.content[0][0]
    assert end_state.state.solver.eval_one(idx) == 7


def test_jni_setarrayregion(binary_dir="4"):
     
    project = create_project(binary_dir)

    end_state = get_last_state_of_method(project=project,
                                         method_fullname="MixedJava.test_jni_setarrayregion1")
    values =  { 'i0':0, 'i1':3, 'i2':2, 'i3':1, 'i4':4 }
    assert_values(end_state, values)

    end_state = get_last_state_of_method(project=project,
                                         method_fullname="MixedJava.test_jni_setarrayregion2")
    a = load_value_from_stack(end_state, 'i1')
    end_state.state.solver.add(a == 2)
    idx = end_state.posix.stdin.content[0][0]
    idx_value = end_state.state.solver.eval_one(idx)
    assert idx_value == 0

    end_state = get_last_state_of_method(project=project,
                                         method_fullname="MixedJava.test_jni_setarrayregion2")
    a = load_value_from_stack(end_state, 'i1')
    end_state.state.solver.add(a == 0)
    idx = end_state.posix.stdin.content[0][0]
    idx_value = end_state.state.solver.eval_exact(idx, 2)
    print idx_value
    assert 1 in idx_value
    assert 2 in idx_value
    assert 3 not in idx_value

def test_jni_getarrayelements_symbolic(binary_dir="4"):
    winning_path = get_winning_path(project=create_project(binary_dir),
                                    method_fullname="MixedJava.test_jni_getarrayelements_symbolic")
    stdin_packets = winning_path.posix.stdin.content
    idx = winning_path.state.solver.eval_one(stdin_packets[0][0])
    min_length = winning_path.state.solver.min(stdin_packets[1][0])
    assert idx == 223
    assert min_length == 224
    print "Found correct solution:", "idx =", idx, ", min_length =", min_length

def test_jni_releasearrayelements(binary_dir="4"):
    end_state = get_last_state_of_method(project=create_project(binary_dir),
                                         method_fullname="MixedJava.test_jni_releasearrayelments")
    values =  {'i0':4, 'i1':3, 'i2':2, 'i3':1, 'i4':0}
    assert_values(end_state, values)

def test_jni_getarrayelements_and_releasearrayelements(binary_dir="4"):
    end_state = get_last_state_of_method(
        project=create_project(binary_dir),
        method_fullname="MixedJava.test_jni_getarrayelements_and_releasearrayelements"
    )
    values = {
        'z1':1, 'b5' :0x0000007f, 's6' :0x00007fff, 'i7' :0x7fffffff, 'l8' :0x7fffffffffffffff, 'c9' : 0xffff,
        'z2':1, 'b10':0xffffff80, 's11':0xffff8000, 'i12':0x80000000, 'l13':0x8000000000000000, 'c14': 0x0000
    } 
    assert_values(end_state, values)

def test_jni_getarraylength(binary_dir="4"):
    end_state = get_last_state_of_method(project=create_project(binary_dir),
                                         method_fullname="MixedJava.test_jni_getarraylength")
    a = end_state.memory.stack.load('i3')
    assert end_state.solver.eval(a) == 10
    b = end_state.memory.stack.load('i4')
    assert end_state.solver.min(b) == 0 
    assert end_state.solver.max(b) == 255

#
# Arrays
#

def test_array_out_of_bounds(binary_dir="4"):
    project = create_project(binary_dir)

    end_state = get_last_state_of_method(project, "MixedJava.test_index_of_of_bound0")
    array_len = load_value_from_stack(end_state, 'i1')
    print "assert array length in range 0-255"
    assert 0 == end_state.solver.min(array_len)
    assert 255 == end_state.solver.max(array_len)

    end_state = get_last_state_of_method(project, "MixedJava.test_index_of_of_bound1")
    array_len = load_value_from_stack(end_state, 'i1')
    print "assert array length in range 101-255"
    assert 101 == end_state.solver.min(array_len)
    assert 255 == end_state.solver.max(array_len)

    end_state = get_last_state_of_method(project, "MixedJava.test_index_of_of_bound2")
    assert load_value_from_stack(end_state, 'i1') != None
    assert load_value_from_stack(end_state, 'i2') == None
    assert load_value_from_stack(end_state, 'i3') == None
    assert load_value_from_stack(end_state, 'i4') != None
    assert load_value_from_stack(end_state, 'i5') == None

    end_state = get_last_state_of_method(project, "MixedJava.test_index_of_of_bound3")
    assert load_value_from_stack(end_state, 'i1') != None
    assert load_value_from_stack(end_state, 'i2') != None
    assert load_value_from_stack(end_state, 'i3') == None
    assert load_value_from_stack(end_state, 'i4') != None
    assert load_value_from_stack(end_state, 'i5') == None

    end_state = get_last_state_of_method(project, "MixedJava.test_index_of_of_bound4")
    assert load_value_from_stack(end_state, 'i1') != None
    assert load_value_from_stack(end_state, 'i2') != None
    assert load_value_from_stack(end_state, 'i3') == None

    end_state = get_last_state_of_method(project, "MixedJava.test_index_of_of_bound5")
    assert load_value_from_stack(end_state, 'i1') != None
    assert load_value_from_stack(end_state, 'i2') != None
    assert load_value_from_stack(end_state, 'i3') == None

def test_symbolic_array_length(binary_dir="4"):
    winning_path = get_winning_path(project=create_project(binary_dir),
                                    method_fullname="MixedJava.test_symbolic_array_length")
    # get input from winning path
    stdin_packets = winning_path.posix.stdin.content
    input_char, _ = stdin_packets[0]
    # eval input
    solution = winning_path.state.solver.eval_one(input_char)
    assert solution == ord('F')
    print "Found correct solution:", chr(solution)

def test_symbolic_array_write(binary_dir="4"):
    winning_path = get_winning_path(project=create_project(binary_dir),
                                    method_fullname="MixedJava.test_symbolic_array_write")
    # get input from winning path
    stdin_packets = winning_path.posix.stdin.content
    idx_symbol, _ = stdin_packets[0]
    val_symbol, _ = stdin_packets[1]
    # eval input
    winning_path.state.solver.add(val_symbol != 0) # exclude trivial solution
    idx = winning_path.state.solver.eval_one(idx_symbol)
    val = winning_path.state.solver.eval_one(val_symbol)
    assert idx == ord('I')
    assert val == ord('5')
    print "Found correct solution:", "idx =", chr(idx), ", val =", chr(val)

def test_symbolic_array_read(binary_dir="4"):
    winning_path = get_winning_path(project=create_project(binary_dir), 
                                    method_fullname="MixedJava.test_symbolic_array_read")
    # get input from winning path
    stdin_packets = winning_path.posix.stdin.content
    input_char, _ = stdin_packets[0]
    # eval input
    solutions = winning_path.state.solver.eval_exact(input_char, 2)
    assert ord('A') in solutions
    assert ord('C') in solutions
    print "Found correct solutions:", chr(solutions[0]), "and", chr(solutions[1])

def test_basic_array_operations(binary_dir="4"):
    end_state = get_last_state_of_method(project=create_project(binary_dir),
                                         method_fullname="MixedJava.test_basic_array_operations")
    values = {'i1': 0, 'i2': 1, 'i3': 2, 'i4': 3, 'i5': 4,'i6': 5, 'i7': 2, 'i8': 0}
    assert_values(end_state, values)

#
# Helper
#

def create_project(binary_dir):
    jar_path = os.path.join(test_location, "mixed_java",
                            binary_dir, "MixedJava.jar")
    jni_options = {'native_libs': ['libmixedjava.so']}
    return angr.Project(jar_path, main_opts=jni_options)


def load_value_from_stack(state, symbol_name):
    try:
        return state.memory.stack.load(symbol_name)
    except KeyError:
        return None

def assert_values(state, values):
    for symbol_name, assert_value in values.items():
        print "assert value of %s:" % symbol_name,
        symbol = load_value_from_stack(state, symbol_name)
        val = state.solver.eval_one(symbol)
        print "should be 0x%x is 0x%x" % (assert_value, val)
        assert val == assert_value


def get_entry_state_of_method(project, method_fullname):
    # get SootAddressDescriptor of method entry
    soot_method = project.loader.main_object.get_method(method_fullname)
    method = SootMethodDescriptor.from_soot_method(soot_method)
    addr = SootAddressDescriptor(method, 0, 0)
    # create call state
    return project.factory.blank_state(addr=addr)

def get_last_state_of_method(project, method_fullname):
    state = get_entry_state_of_method(project, method_fullname)
    # run until no successors exists
    # Note: this does not work if conditional branches are present
    states = [state]
    succ = states[-1].step()
    while len(succ.successors) == 1:
        states += succ
        succ = states[-1].step()
    # last state is the 'Terminator' state
    # => return the state before
    return states[-2]

def get_winning_paths(project, method_fullname):
    state = get_entry_state_of_method(project, method_fullname)
    simgr = project.factory.simgr(state)
    simgr.run()
    paths = simgr.deadended
    
    # winning paths output a single 'W' on stdout
    winnning_paths = []
    for pp in paths:
        stdout_packets = pp.posix.stdout.content
        read_byte, _ = stdout_packets[0]
        # a winning path is printing 'W'
        pp.state.add_constraints(read_byte == pp.state.solver.BVV(ord('W'), 8))
        if pp.satisfiable():
            winnning_paths.append(pp)

    return winnning_paths

def get_winning_path(project, method_fullname):
    winning_paths = get_winning_paths(project, method_fullname)
    assert len(winning_paths) != 0
    assert len(winning_paths) == 1
    return winning_paths[0]


def main():
    #test_loading_of_native_libs_with_ld_path()
    #test_loading_of_native_libs_without_ld_path()
    test_jni_env_get_version()
    test_primitive_types()


if __name__ == "__main__":
    main()
