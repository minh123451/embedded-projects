#include <stdint.h>

#ifndef STM32F103C8T6_H_
#define STM32F103C8T6_H_

#define APB1_BASE_ADD			0x40000000UL
#define APB2_BASE_ADD			0x40010000UL
#define AHB_BASE_ADD			0x40018000UL

//GPIO BASE ADDRESS
#define GPIOA_BASE_ADD 		0x40010800UL 
#define GPIOB_BASE_ADD 		0x40010C00UL
#define GPIOC_BASE_ADD 		0x40011000UL
#define GPIOD_BASE_ADD 		0x40011400UL
#define GPIOE_BASE_ADD 		0x40011800UL
#define GPIOF_BASE_ADD 		0x40011C00UL
#define GPIOG_BASE_ADD 		0x40012000UL

// RCC BASE ADDRESS
#define RCC_BASE_ADD  		0x40021000UL

// struct cho RCC câp xung clock
typedef struct {
    volatile uint32_t CR;        // 0x00
    volatile uint32_t CFGR;      // 0x04
    volatile uint32_t CIR;       // 0x08
    volatile uint32_t APB2RSTR;  // 0x0C
    volatile uint32_t APB1RSTR;  // 0x10
    volatile uint32_t AHBENR;    // 0x14
    volatile uint32_t APB2ENR;   // 0x18
    volatile uint32_t APB1ENR;   // 0x1C
    volatile uint32_t BDCR;      // 0x20
    volatile uint32_t CSR;       // 0x24
} RCC_typedef;

// struct cho các gpio 
typedef struct {
	volatile uint32_t 			CRL;															//Address offset 	0x00
	volatile uint32_t 			CRH;															//Address offset 	0x04
	volatile uint32_t 			IDR;															//Address offset 	0x08
	volatile uint32_t 			ODR;            									//Address offset 	0x0C
	volatile uint32_t 			BSRR;           									//Address offset 	0x10
	volatile uint32_t 			BRR;            									//Address offset 	0x14
	volatile uint32_t 			LCKR;           									//Address offset 	0x18
}GPIO_typedef;

// struct cho AFIO                                          
typedef struct {                                           
	volatile uint32_t 			EVCR;                             //Address offset 	0x00
	volatile uint32_t 			MAPR;                             //Address offset 	0x04
	volatile uint32_t 			EXTICR[3];                        //Address offset 	0x08,0x0C,0x10,0x14
	volatile uint32_t 			MAPR2;														//Address offset 	0x1C
}AFIO_typedef;                                             

// struct cho EXTI
typedef struct {
	volatile uint32_t 			IMR;															//Address offset 	0x00
	volatile uint32_t 			EMR;                              //Address offset 	0x04
	volatile uint32_t 			RTSR;                             //Address offset 	0x08
	volatile uint32_t 			FTSR;                             //Address offset 	0x0C
	volatile uint32_t 			SWIER;                            //Address offset 	0x10
	volatile uint32_t 			PR;																//Address offset 	0x14
}EXTI_typedef;   

// struct cho spi
typedef struct {
	volatile uint32_t 			CR1;                //Address offset 	0x00
	volatile uint32_t 			CR2;                //Address offset 	0x04
	volatile uint32_t 			SR;                 //Address offset 	0x08
	volatile uint32_t 			DR;                 //Address offset 	0x0C
	volatile uint32_t 			CRCPR;              //Address offset 	0x10
	volatile uint32_t 			RXCRCR;             //Address offset 	0x14
	volatile uint32_t 			TXCRCR;             //Address offset 	0x18
	volatile uint32_t 			I2SCFGR;            //Address offset 	0x1C
	volatile uint32_t 			I2SPR;							//Address offset 	0x20
}SPI_typedef;                                             
                                                            
// define EXTI_ADDRESS                                
#define EXTI 				((EXTI_typedef*)0x40010400UL)

// define AFIO_ADDRESS 
#define AFIO  			((AFIO_typedef *)0x40010000UL)

// define NVIC_IPR_ADDRESS
#define NVIC_IPR_ADDRESS					(volatile uint32_t*)0xE000E400UL
	
// define SPI_ADDRESS			
#define SPI1_ADDRESS			(SPI_typedef*)0x40013000UL
#define SPI2_ADDRESS			(SPI_typedef*)0x40003800UL
#define SPI3_ADDRESS			(SPI_typedef*)0x40003C00UL

//define ADDRESS FOR GPIO 
#define GPIOA 			((GPIO_typedef *)GPIOA_BASE_ADD)
#define GPIOB 			((GPIO_typedef *)GPIOB_BASE_ADD)
#define GPIOC 			((GPIO_typedef *)GPIOC_BASE_ADD)
#define GPIOD 			((GPIO_typedef *)GPIOD_BASE_ADD)
#define GPIOE 			((GPIO_typedef *)GPIOE_BASE_ADD)
//#define GPIOF 			((GPIO_typedef *)GPIOF_BASE_ADD)
//#define GPIOG 			((GPIO_typedef *)GPIOG_BASE_ADD)

// thiet lap RCC cho xong clock
#define RCC 				((RCC_typedef *) RCC_BASE_ADD)

// enable clock for GPIOs 
#define GPIOA_CLK_EN()			(RCC->APB2ENR |= (1 << 2))
#define GPIOB_CLK_EN()			(RCC->APB2ENR |= (1 << 3))
#define GPIOC_CLK_EN()			(RCC->APB2ENR |= (1 << 4))
#define GPIOD_CLK_EN()			(RCC->APB2ENR |= (1 << 5))
#define GPIOE_CLK_EN()			(RCC->APB2ENR |= (1 << 6))

// unable clock for GPIOs
#define GPIOA_CLK_DIS()			(RCC->APB2ENR &= ~(1 << 2))
#define GPIOB_CLK_DIS()			(RCC->APB2ENR &= ~(1 << 3))
#define GPIOC_CLK_DIS()			(RCC->APB2ENR &= ~(1 << 4))
#define GPIOD_CLK_DIS()			(RCC->APB2ENR &= ~(1 << 5))
#define GPIOE_CLK_DIS()			(RCC->APB2ENR &= ~(1 << 6))

// reset clock for GPIOs
#define GPIOA_RESET()				do{RCC->APB2RSTR |= (1 << 2);RCC->APB2RSTR &= ~(1 << 2);}while(0) 
#define GPIOB_RESET() 			do{RCC->APB2RSTR |= (1 << 3);RCC->APB2RSTR &= ~(1 << 3);}while(0) 
#define GPIOC_RESET() 			do{RCC->APB2RSTR |= (1 << 4);RCC->APB2RSTR &= ~(1 << 4);}while(0) 
#define GPIOD_RESET() 			do{RCC->APB2RSTR |= (1 << 5);RCC->APB2RSTR &= ~(1 << 5);}while(0) 
#define GPIOE_RESET()				do{RCC->APB2RSTR |= (1 << 6);RCC->APB2RSTR &= ~(1 << 6);}while(0) 

// enable clock for SPI
#define SPI1_EN()						(RCC->APB2ENR |= (1 << 12))
#define SPI2_EN()						(RCC->APB1ENR |= (1 << 14))
#define SPI3_EN()						(RCC->APB1ENR |= (1 << 15))

// disable clock for SPI
#define SPI1_DIS()					(RCC->APB2ENR &= ~(1 << 12))
#define SPI2_DIS()					(RCC->APB1ENR &= ~(1 << 14))
#define SPI3_DIS()					(RCC->APB1ENR &= ~(1 << 15)) 


// define port cho AFIO dê câu hình interupt 
#define PORT(x)  ((x == GPIOA) ? 0 : (x == GPIOB) ? 1 :  (x == GPIOC) ? 2 : (x == GPIOD) ? 3 : 4)

// define các IRQ phuc vu xu lý ngat
#define IRQ_EXTI0 					6
#define IRQ_EXTI1 					7
#define IRQ_EXTI2 					8
#define IRQ_EXTI3 					9
#define IRQ_EXTI4 					10
#define IRQ_EXTI5_9 				23
#define IRQ_EXTI10_15 			40

// define NVIC de kich hoat ngat 
#define NVIC_ISER0 							(volatile uint32_t*)0xE000E100UL
#define NVIC_ISER1 							(volatile uint32_t*)0xE000E104UL
#define NVIC_ISER2 							(volatile uint32_t*)0xE000E108UL

	
// define NVIC xóa các interrupt dã kich hoat
#define NVIC_ICER0 							(volatile uint32_t*)0xE000E180UL
#define NVIC_ICER1 							(volatile uint32_t*)0xE000E184UL
#define NVIC_ICER2 							(volatile uint32_t*)0xE000E188UL


// enable i2c
#define I2C_1_EN()					(RCC->APB1ENR |= (1 << 21))
#define I2C_2_EN()					(RCC->APB1ENR |= (1 << 22))

//dinh nghia các muc cho enble và set, reset
#define ENABLE					1
#define DISABLE					0
#define SET 						1
#define RESET						0

// dinh nghia cac trigger canh lên xuông 
#define EN_RTSR 				1
#define EN_FTSR					0

#endif