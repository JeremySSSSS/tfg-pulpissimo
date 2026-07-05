#include <math.h>

#define ITERATIONS 10

static float x1, x2, x3, x4, x, y, z, t, t1, t2;
static float e1[4];
static int i, j, k, l, n1, n2, n3, n4, n6, n7, n8, n9, n10, n11;

static void pa(float e[])
{
    for (j = 0; j < 6; j++) {
        e[0] = (e[0] + e[1] + e[2] - e[3]) * t;
        e[1] = (e[0] + e[1] - e[2] + e[3]) * t;
        e[2] = (e[0] - e[1] + e[2] + e[3]) * t;
        e[3] = (-e[0] + e[1] + e[2] + e[3]) / t2;
    }
}

static void p3(float xx, float yy, float *zz)
{
    float x1l = xx;
    float y1l = yy;
    x1l = t * (x1l + y1l);
    y1l = t * (x1l + y1l);
    *zz = (x1l + y1l) / t2;
}

void run_workload(void)
{
    int loop;

    t = 0.499975f;
    t1 = 0.50025f;
    t2 = 2.0f;

    n1 = 0 * ITERATIONS;
    n2 = 12 * ITERATIONS;
    n3 = 14 * ITERATIONS;
    n4 = 345 * ITERATIONS;
    n6 = 210 * ITERATIONS;
    n7 = 32 * ITERATIONS;
    n8 = 899 * ITERATIONS;
    n9 = 616 * ITERATIONS;
    n10 = 0 * ITERATIONS;
    n11 = 93 * ITERATIONS;

    x1 = 1.0f;
    x2 = x3 = x4 = -1.0f;
    for (i = 1; i <= n1; i++) {
        x1 = (x1 + x2 + x3 - x4) * t;
        x2 = (x1 + x2 - x3 + x4) * t;
        x3 = (x1 - x2 + x3 + x4) * t;
        x4 = (-x1 + x2 + x3 + x4) * t;
    }

    e1[0] = 1.0f;
    e1[1] = e1[2] = e1[3] = -1.0f;
    for (i = 1; i <= n2; i++) {
        e1[0] = (e1[0] + e1[1] + e1[2] - e1[3]) * t;
        e1[1] = (e1[0] + e1[1] - e1[2] + e1[3]) * t;
        e1[2] = (e1[0] - e1[1] + e1[2] + e1[3]) * t;
        e1[3] = (-e1[0] + e1[1] + e1[2] + e1[3]) * t;
    }

    for (i = 1; i <= n3; i++)
        pa(e1);

    j = 1;
    for (i = 1; i <= n4; i++) {
        if (j == 1) j = 2; else j = 3;
        if (j > 2) j = 0; else j = 1;
        if (j < 1) j = 1; else j = 0;
    }

    j = 1;
    k = 2;
    l = 3;
    for (i = 1; i <= n6; i++) {
        j = j * (k - j) * (l - k);
        k = l * k - (l - j) * k;
        l = (l - k) * (k + j);
        e1[l - 1] = (float)(j + k + l);
        e1[k - 1] = (float)(j * k * l);
    }

    x = 0.5f;
    y = 0.5f;
    for (i = 1; i <= n7; i++) {
        x = t * atanf(t2 * sinf(x) * cosf(x) /
                      (cosf(x + y) + cosf(x - y) - 1.0f));
        y = t * atanf(t2 * sinf(y) * cosf(y) /
                      (cosf(x + y) + cosf(x - y) - 1.0f));
    }

    x = 1.0f;
    y = 1.0f;
    z = 1.0f;
    for (i = 1; i <= n8; i++)
        p3(x, y, &z);

    j = 1;
    k = 2;
    l = 3;
    e1[0] = 1.0f;
    e1[1] = 2.0f;
    e1[2] = 3.0f;
    for (i = 1; i <= n9; i++) {
        float tmp = e1[j - 1];
        e1[j - 1] = e1[k - 1];
        e1[k - 1] = e1[l - 1];
        e1[l - 1] = tmp;
    }

    j = 2;
    k = 3;
    for (i = 1; i <= n10; i++) {
        j = j + k;
        k = j + k;
        j = k - j;
        k = k - j - j;
    }

    x = 0.75f;
    for (i = 1; i <= n11; i++)
        x = sqrtf(expf(logf(x) / t1));

    loop = 0;
    (void)loop;
    gpio_low;
    for (;;)
        wfi;
}
