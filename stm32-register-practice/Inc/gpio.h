	
#ifndef 	INC_gpio_H_
#define 	INC_gpio_H_
#include "stm32f103c8t6.h"

// dinh nghia GPIO mode 

#define InMode						 					0
#define OutMode_Speed_10Mhz 				1
#define OutMode_Speed_2Mhz					2	
#define OutMode_Speed_50Mhz					3

// dinh nghia CNF for input 

#define Input_Analog								0
#define Input_Floating 							1
#define Input_Pull_UD 							2

// dinh nghia CNF for output

#define Output_PushPull 						0
#define Output_	OpenDrain 					1
#define Output_Alter_PushPull 			2
#define Output_Alter_OpenDrain 			3

// GPIO pin number 

#define GPIO_Pin_0 				0
#define GPIO_Pin_1 				1
#define GPIO_Pin_2 				2
#define GPIO_Pin_3 				3
#define GPIO_Pin_4 				4
#define GPIO_Pin_5 				5
#define GPIO_Pin_6 				6
#define GPIO_Pin_7 				7
#define GPIO_Pin_8 				8
#define GPIO_Pin_9 				9
#define GPIO_Pin_10 			10
#define GPIO_Pin_11 			11
#define GPIO_Pin_12 			12
#define GPIO_Pin_13 			13
#define GPIO_Pin_14 			14
#define GPIO_Pin_15 			15

//config tung chan cho gpio 
typedef struct 
{
	uint8_t 		GPIO_PinNumber;
	uint8_t 		GPIO_PinMode;
	uint8_t 		GPIO_PinCNF;
}GPIO_Pin_config;

// quan ly gpiox 
typedef struct
{
	GPIO_typedef *GPIOx;
	GPIO_Pin_config GPIO_Pinconfig;
}GPIO_Handle_t;

// peripheral clock set up 

void GPIO_PeriClockControl(GPIO_typedef *GPIOx, uint8_t en_dis);

// Init and De_init for gpio 

void GPIO_Init(GPIO_Handle_t *pGPIO_Handle);
void GPIO_DeInit(GPIO_typedef *GPIOx);
	
// gpio read and write data

uint8_t GPIO_ReadFromInputPin(GPIO_typedef *GPIOx, uint8_t PinNumber);
uint16_t GPIO_ReadFromInputPort(GPIO_typedef *GPIOx);
void GPIO_WriteToOutputPin(GPIO_typedef *GPIOx, uint8_t PinNumber, uint8_t value);
void GPIO_WriteToOuputPort(GPIO_typedef *GPIOx, uint8_t value);
void GPIO_ToggleOutputPin(GPIO_typedef *GPIOx, uint8_t PinNumber);

// hàm config interrupt 

void GPIO_ConfigInterrupt(uint8_t PinNumber, uint8_t TriggerType, GPIO_typedef *GPIOx);
void GPIO_IRQ_config(uint8_t IRQ_Number, uint8_t setORclear );
void GPIO_IRQ_priority_config(uint8_t IRQ_Number, uint8_t priority);
uint8_t get_GPIO_Pending(uint8_t PinNumber);
void clear_GPIO_Pending(uint8_t PinNumber);


#endif