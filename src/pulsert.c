#include <stdio.h>

// __declspec(dllexport)      // Uncomment on Windows
void _print_int(int x) {
  printf("%i\n", x);
}

// __declspec(dllexport)     // Uncomment on Windows
void _print_float(double x) {
  printf("%f\n", x);
}

// __declspec(dllexport)    // Uncomment on Windows
void _print_byte(char c) {
  printf("%c", c);
  fflush(stdout);
}

/* Bootstrapping code for a stand-alone executable */

#ifdef NEED_MAIN
extern void __pulse_init(void);
extern int __pulse_main(void);

int main() {
  __pulse_init();
  return __pulse_main();
}
#endif
