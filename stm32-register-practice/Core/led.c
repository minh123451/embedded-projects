#include "stm32f103c8t6.h"
#include "gpio.h"

void delay(uint16_t ms){
    for(uint16_t i = 0 ; i < ms ; i++){
        for(uint16_t j = 0 ; j < 50000 ; j++);
    }
}

int main(void){
	

    GPIO_Handle_t led;

    led.GPIOx = GPIOC;
    led.GPIO_Pinconfig.GPIO_PinMode = OutMode_Speed_2Mhz;
    led.GPIO_Pinconfig.GPIO_PinCNF = Output_PushPull;
    led.GPIO_Pinconfig.GPIO_PinNumber = GPIO_Pin_13;

//    GPIO_PeriClockControl(GPIOC, ENABLE);
    GPIO_Init(&led);

    while(1){
			GPIO_ToggleOutputPin(GPIOC, GPIO_Pin_13);
			delay(200);
    }
}
