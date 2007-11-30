program gather("P=P:,R=R:")

%%#include <stdio.h>
%%#include <stdlib.h>

option +r;

int trigger; assign trigger to "{P}{R}trigger.VAL";
monitor trigger;

ss ssGather 
{
	state init 
	{
		when()
		{
			printf("ssGather: state init entry.\n");
			trigger = 1;
			pvPut(trigger);
		} state monitor_inputs
	}

	state monitor_inputs
	{
		entry
		{
			printf("ssGather: state monitor_inputs.\n");
		}
		when( trigger == 1 )
		{
			printf("ssGather: Got trigger!\n");
			printf("ssGather: sending gather command to PMAC.\n");
		} state acquire
	}
	
	state acquire
	{
		entry
		{
			trigger = 0;
			pvPut(trigger);
			printf("ssGather: state acquire entry.\n");
		}
		when(delay(10.0))
		{
			printf("ssGather: waited long enough for acquire to finish...\n");
		} state collect
	}

	state collect
	{
		entry
		{
			printf("ssGather: state collect\n");
		}
		when()
		{
			printf("ssGather: sending the list gather command to PMAC.\n");
			printf("ssGather: parsing the gathered data from the PMAC.\n");
			
		} state monitor_inputs
	}
}
		
