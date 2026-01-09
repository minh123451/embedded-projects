#include "stm32f103c8t6.h"
#include "gpio.h"

void EXTI2_IRQHandler(void){
	if(get_GPIO_Pending(GPIO_Pin_2)){
		GPIO_ToggleOutputPin(GPIOA, GPIO_Pin_1);
		//xóa co pending de dóng su kien isr 
		clear_GPIO_Pending(GPIO_Pin_2);
	}
}


void config(void){
	// khoi tao led 
	GPIO_Handle_t led ; 
	led.GPIOx = GPIOA;
	led.GPIO_Pinconfig.GPIO_PinNumber = GPIO_Pin_1;
	led.GPIO_Pinconfig.GPIO_PinMode = OutMode_Speed_50Mhz;
	led.GPIO_Pinconfig.GPIO_PinCNF = Output_PushPull;
	GPIO_Init(&led);


	// cau hình interrupt 

	GPIO_Handle_t button ; 
	button.GPIOx = GPIOA;
	button.GPIO_Pinconfig.GPIO_PinNumber = GPIO_Pin_2;
	button.GPIO_Pinconfig.GPIO_PinMode = InMode;
	button.GPIO_Pinconfig.GPIO_PinCNF = Input_Pull_UD;
	GPIO_Init(&button);

	GPIO_ConfigInterrupt(GPIO_Pin_2, EN_FTSR, GPIOA);
	GPIO_IRQ_config(IRQ_EXTI2, ENABLE );
	GPIO_IRQ_priority_config(IRQ_EXTI2, 4);
	//GPIO_Pending(GPIO_Pin_2);
}
	

int main_2(void){
	config();
	GPIO_WriteToOutputPin(GPIOA, GPIO_Pin_1, RESET);
	int cnt = 0 ; 
	while(1){
		cnt ++;
	}
	return 0 ; 
}