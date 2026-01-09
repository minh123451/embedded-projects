# STM32F103 Register-Level Programming

Bare-metal programming project on **STM32F103C8T6** using direct register access and self-written GPIO driver (no HAL).

## Features
- GPIO output configuration and LED blinking
- External interrupt (EXTI) configuration and handling
- Interrupt-driven LED control
- Manual EXTI pending flag management

## System Overview
- STM32F103C8T6 microcontroller
- GPIO configured in Push-Pull and Input Pull-Up/Down modes
- EXTI line configured with NVIC interrupt
- LED toggled inside interrupt service routine

## Technologies
STM32F103C8T6, Embedded C, Register-Level Programming, GPIO, EXTI, NVIC

## Author
Lam Nguyen Gia Minh
