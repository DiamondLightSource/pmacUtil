program gather("P=P:,R=R:")

%%#include <stdio.h>
%%#include <stdlib.h>
%%#include <string.h>
option +r;

int execute; assign execute to "{P}{M}:EXECUTE.VAL";
monitor execute;
evflag executeMon; sync execute executeMon;

#define MAX_RAW_CHARS 13315
char rawData[MAX_RAW_CHARS]; assign rawData to "{P}{M}:GETDATA.BINP";
monitor rawData;
evflag rawDataMon; sync rawData rawDataMon;

int nRawChars; assign nRawChars to "{P}{M}:GETDATA.NORD";
monitor nRawChars;

string stateMsg; assign stateMsg to "{P}{M}:STATE.VAL";

ss ssGather 
{
	state INIT 
	{
		entry
		{
			printf("ssGather: state INIT entry.\n");
			strcpy(stateMsg, "INIT");
			pvPut(stateMsg);
		}
		when()
		{
			printf("ssGather: clearing all event flags.\n");
			efClear(executeMon);
			efClear(rawDataMon);
		} state READY
	}

	state READY
	{
		entry
		{
			printf("ssGather: state READY\n");
			strcpy(stateMsg, "READY");
			pvPut(stateMsg);
		}
		when( efTestAndClear(executeMon) && (execute == 1) )
		{
			printf("ssGather: got execute trigger from user.\n");
		} state SETUP
	}
	
	state SETUP
	{
		entry
		{
			printf("ssGather: state SETUP\n");
			strcpy(stateMsg, "SETUP");
			pvPut(stateMsg);
		}
		when()
		{
			printf("ssGather: setting up all ivars for gathering\n");

		} state GATHER
	}

	state GATHER
	{
		entry
		{
			printf("ssGather: state GATHER\n");
			strcpy(stateMsg, "GATHER");
			pvPut(stateMsg);
			printf("ssGather: sending define gather cmd to start gathering.\n");
			printf("ssGather: sending tweak step command to motor to start moving.\n");

		}
		when(delay(10.0))
		{
			printf("ssGather: timeout - gathering must have stopped now...(I guess)\n");
			
		} state COLLECT
	}

	state COLLECT
	{
		entry
		{
			printf("ssGather: state COLLECT\n");
			strcpy(stateMsg, "COLLECT");
			pvPut(stateMsg);
			printf("ssGather: sending list gather cmd to collect data from PMAC.\n");
		}
		when( efTestAndClear(rawDataMon) )
		{
			printf("ssGather: got raw data: %d ASCII chars!\n", nRawChars);
		} state PARSE
	}

	state PARSE
	{
		entry
		{
			printf("ssGather: state PARSE\n");
			strcpy(stateMsg, "PARSE");
			pvPut(stateMsg);
		}
		when()
		{
			printf("ssGather: parsing the raw ASCII data...\n");
			printf("ssGather: posting the parsed data to the waveform records.\n");
			printf("ssGather: all done!\n");
			execute = 0;
			pvPut(execute);
			efClear(executeMon);
		} state READY
	}
}

