#include "gpio.h"


void GPIO_PeriClockControl(GPIO_typedef *GPIOx, uint8_t en_dis){
	if(en_dis == ENABLE){
		if(GPIOx == GPIOA){
			GPIOA_CLK_EN();
		}	
		else if(GPIOx == GPIOB){
			GPIOB_CLK_EN();
		}
		else if(GPIOx == GPIOC){
			GPIOC_CLK_EN();
		}
		else if(GPIOx == GPIOD){
			GPIOD_CLK_EN();
		}
		else if(GPIOx == GPIOE){
			GPIOE_CLK_EN();
		}
	}	
	else {
		if(GPIOx == GPIOA){
			GPIOA_CLK_DIS();
		}	
		else if(GPIOx == GPIOB){
			GPIOB_CLK_DIS();
		}
		else if(GPIOx == GPIOC){
			GPIOC_CLK_DIS();
		}
		else if(GPIOx == GPIOD){
			GPIOD_CLK_DIS();
		}
		else if(GPIOx == GPIOE){
			GPIOE_CLK_DIS();
		}	
	}
} 

//hàm khoi tao cac GPIO

void GPIO_Init(GPIO_Handle_t *pGPIO_Handle)
{
    GPIO_PeriClockControl(pGPIO_Handle->GPIOx, ENABLE);

    uint32_t temp = 0;

    // T?o 4 bit config: MODE[1:0] + CNF[1:0]
    temp = (pGPIO_Handle->GPIO_Pinconfig.GPIO_PinMode 
           | (pGPIO_Handle->GPIO_Pinconfig.GPIO_PinCNF << 2));

    if (pGPIO_Handle->GPIO_Pinconfig.GPIO_PinNumber < 8)
    {
        uint8_t shift = 4 * pGPIO_Handle->GPIO_Pinconfig.GPIO_PinNumber;
        pGPIO_Handle->GPIOx->CRL &= ~(0xF << shift);
        pGPIO_Handle->GPIOx->CRL |= (temp << shift);
    }
    else
    {
        uint8_t shift = 4 * (pGPIO_Handle->GPIO_Pinconfig.GPIO_PinNumber - 8);
        pGPIO_Handle->GPIOx->CRH &= ~(0xF << shift);
        pGPIO_Handle->GPIOx->CRH |= (temp << shift);
    }

    // N?u là input pull-up / pull-down thì c?n c?u hình thêm ODR
    if (pGPIO_Handle->GPIO_Pinconfig.GPIO_PinMode == InMode &&
        pGPIO_Handle->GPIO_Pinconfig.GPIO_PinCNF == Input_Pull_UD)
    {
        // pull-up
        pGPIO_Handle->GPIOx->ODR |= (1 << pGPIO_Handle->GPIO_Pinconfig.GPIO_PinNumber);
        // n?u mu?n pull-down thì clear bit:
        // pGPIO_Handle->GPIOx->ODR &= ~(1 << pGPIO_Handle->GPIO_Pinconfig.GPIO_PinNumber);
    }
}

// hàm de_init cho các gpio 

void GPIO_DeInit(GPIO_typedef *GPIOx){
	if(GPIOx == GPIOA){
		GPIOA_RESET();
	}
	if(GPIOx == GPIOB){
		GPIOB_RESET();
	}
	if(GPIOx == GPIOC){
		GPIOC_RESET();
	}
	if(GPIOx == GPIOD){
		GPIOD_RESET();
	}
	if(GPIOx == GPIOE){
		GPIOE_RESET();
	}
}

// hàm read tu pin_gpio

uint8_t GPIO_ReadFromInputPin(GPIO_typedef *GPIOx, uint8_t PinNumber){
	uint8_t value ;
	value = (uint8_t)(GPIOx->IDR >> PinNumber) & 0x00000001;
	return value;
}

// hàm read port gpio 

uint16_t GPIO_ReadFromInputPort(GPIO_typedef *GPIOx){
	uint16_t value;
	value = (uint16_t)(GPIOx->IDR);
	return value;
}

// hàm write write pin gpio 

void GPIO_WriteToOutputPin(GPIO_typedef *GPIOx, uint8_t PinNumber, uint8_t value){
	if(value == SET){
		GPIOx->ODR |= (1 << PinNumber);
	}
	else {
		GPIOx->ODR &= ~(1 << PinNumber);
	}
}

// hàm write port gpio 

void GPIO_WriteToOuputPort(GPIO_typedef *GPIOx, uint8_t value){
	GPIOx->ODR = value;
}

// hàm Toggle pin gpio

void GPIO_ToggleOutputPin(GPIO_typedef *GPIOx, uint8_t PinNumber){
	GPIOx->ODR ^= (1 << PinNumber);
}


// hàm câu hình Interrupt 

void GPIO_ConfigInterrupt(uint8_t PinNumber, uint8_t TriggerType, GPIO_typedef *GPIOx){
	RCC->APB2ENR |= (1 << 0);
	if(TriggerType == EN_RTSR)
	{
		EXTI->RTSR |= (1 << PinNumber);
		EXTI->FTSR &= ~(1 << PinNumber);
	}
	else if (TriggerType == EN_FTSR)
	{
		EXTI->FTSR |= (1 << PinNumber);
		EXTI->RTSR &= ~(1 << PinNumber);		
	}
	uint8_t temp1 = PinNumber / 4;
	uint8_t temp2 = PinNumber % 4;
	
	// lua chon port và chân cho câu hinh interrup
	AFIO->EXTICR[temp1] &= ~(0xF) << 4 * temp2;  // clear
	AFIO->EXTICR[temp1] |= (PORT(GPIOx) << 4 * temp2);  // set
	
	EXTI->IMR |= (1 << PinNumber);
}

// hàm cáu hih IRQ trên cpu 

void GPIO_IRQ_config(uint8_t IRQ_Number, uint8_t setORclear ){
	if(setORclear == ENABLE)
	{
		if(IRQ_Number < 32)
		{
			*NVIC_ISER0 = (1 << IRQ_Number);
		}
		else if (IRQ_Number >= 32 && IRQ_Number <= 64)
		{
			*NVIC_ISER1 = (1 << IRQ_Number % 32) ;
		}
		else if (IRQ_Number >= 65 && IRQ_Number <= 97)
		{
			*NVIC_ISER2 = (1 << IRQ_Number % 32) ;
		}
	}
	else {
		if(IRQ_Number < 32)
		{
			*NVIC_ICER0 = (1 << IRQ_Number);
		}
		else if (IRQ_Number >= 32 && IRQ_Number <= 64)
		{
			*NVIC_ICER1 = (1 << IRQ_Number % 32) ;
		}
		else if (IRQ_Number >= 65 && IRQ_Number <= 97)
		{
			*NVIC_ICER2 = (1 << IRQ_Number % 32) ;
		}
	}
}

// hàm set do uu tien trong trong NVIC
void GPIO_IRQ_priority_config(uint8_t IRQ_Number, uint8_t priority){
	uint8_t ipr_index = IRQ_Number / 4;
	uint8_t section = IRQ_Number % 4;
	
	uint8_t shift = 8 * section + 4;
	
	// xóa các NIVC priority dã cau hình tru?c 
	*(NVIC_IPR_ADDRESS + ipr_index) &= ~(0xF << shift ); 
	// set lai  priority mong mu?n 
	*(NVIC_IPR_ADDRESS + ipr_index) |= (priority << shift);
}

uint8_t get_GPIO_Pending(uint8_t PinNumber){
	// kiêm tra xem o vi tri pin gpio do có dang = 1 khong
	return (EXTI->PR & (1 << PinNumber)) ? 1 : 0; 
}

void clear_GPIO_Pending(uint8_t PinNumber){	
	EXTI->PR |= (1 << PinNumber);
}
