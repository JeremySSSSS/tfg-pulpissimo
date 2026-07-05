#include "platform.inc"

extern void kernel_(double tk[6]);
extern void space_(void);

void run_workload(void)
{
    double tk[6] = {0};
    space_();
    kernel_(tk);
}
