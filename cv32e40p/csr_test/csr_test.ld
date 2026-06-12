ENTRY(_start)

MEMORY {
    L2 (rwx) : ORIGIN = 0x1c008000, LENGTH = 64K
}

SECTIONS {
    . = 0x1c008000;
    .text : { *(.text) } > L2
    .data : { *(.data) } > L2
    .bss  : { *(.bss)  } > L2
}
