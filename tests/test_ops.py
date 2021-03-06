import angr
import claripy
import archinfo

def test_irop_perm():
    arch = archinfo.ArchAMD64()
    p = angr.load_shellcode(arch.asm('vpshufb xmm0,xmm1,xmm2'), arch)

    # concrete test
    s1 = p.factory.blank_state()
    s1.regs.xmm1 = 0x3c899a56814ee9b84c7b5d8394c85881
    s1.regs.xmm2 = 0xa55c66a2cdef1cbcd72b42078d1b7f8b
    s2 = s1.step(num_inst=1).successors[0]
    assert (s2.regs.xmm0 == 0x00567b00000056000081c84c00813c00).is_true()

    # symbolic test
    s3 = p.factory.blank_state()
    s3.regs.xmm1 = claripy.BVS('xmm1', 128)
    s3.regs.xmm2 = claripy.BVS('xmm2', 128)
    s4 = s3.step(num_inst=1).successors[0]
    s4.solver.add(s4.regs.xmm2 == 0xa55c66a2cdef1cbcd72b42078d1b7f8b)
    s4.solver.add(s4.regs.xmm0 == 0x00567b00000056000081c84c00813c00)
    assert s4.solver.solution(s4.regs.xmm1, 0x3c899a56814ee9b84c7b5d8394c85881)

def test_mul_hi():
    arch = archinfo.ArchAMD64()
    p = angr.load_shellcode(arch.asm('vpmulhw xmm0,xmm1,xmm2'), arch)

    # concrete test
    s1 = p.factory.blank_state()
    s1.regs.xmm1 = 0x3aca92553c2526d4f20987aeab250255
    s1.regs.xmm2 = 0x1aebcb281463274ec3ce6473619a8541
    s2 = s1.step(num_inst=1).successors[0]
    assert (s2.regs.xmm0 == 0x62e16a304ca05f60348d0c9dfa5fee1).is_true()


if __name__ == '__main__':
    test_irop_perm()
