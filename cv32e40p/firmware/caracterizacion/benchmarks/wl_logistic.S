	.file	"wl_logistic.c"
	.option nopic
	.text
	.align	1
	.globl	run_workload
	.type	run_workload, @function
run_workload:
	lui	a4,%hi(.LC0)
	flw	fa5,%lo(.LC0)(a4)
	lui	a4,%hi(.LC1)
	flw	fa2,%lo(.LC1)(a4)
	lui	a4,%hi(.LC2)
	flw	fa3,%lo(.LC2)(a4)
	li	a5,7999488
	add	sp,sp,-16
	add	a5,a5,512
.L2:
	fmul.s	fa4,fa5,fa2
	fsub.s	fa5,fa3,fa5
	add	a5,a5,-1
	fmul.s	fa5,fa4,fa5
	bnez	a5,.L2
	lui	a5,%hi(.LC3)
	flw	fa4,%lo(.LC3)(a5)
	fmul.s	fa5,fa5,fa4
	fcvt.w.s a5,fa5,rtz
	sw	a5,12(sp)
	lw	a5,12(sp)
	add	sp,sp,16
	jr	ra
	.size	run_workload, .-run_workload
	.section	.srodata.cst4,"aM",@progbits,4
	.align	2
.LC0:
	.word	1056964608
.LC1:
	.word	1081711002
.LC2:
	.word	1065353216
.LC3:
	.word	1148846080
	.ident	"GCC: (GNU) 7.1.1 20170509"
