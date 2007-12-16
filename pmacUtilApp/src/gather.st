program gather("P=P,R=:M")

%%#include <stdio.h>
%%#include <stdlib.h>
%%#include <string.h>
option +r;
/* number of raw chars to receive from gathering 
   = 3 data sources x 1024 samples x (12 hex-chars + 1 lineend) + 2 end of stream chars
   = 39938 chars 
   Rounded to 40K = 40960
 */
   
#define MAX_RAW_CHARS 40960
#define N_ELEMENTS 1024
#define MAX_N_DATASRC 3
#define MAX_PV_STR_LEN 30

int execute; 					assign execute 			to "{P}{M}:EXECUTE.VAL";
string motor;					assign motor	 		to "{P}{M}:MOTOR";
string moveOut; 				assign moveOut 			to "{P}{M}:MOVE.OUT";
double moveVal; 				assign moveVal 			to "{P}{M}:MOVE.VAL";
double demandVal; 				assign demandVal 		to "{P}{M}:DEMAND.VAL";
string mrbvInpA; 				assign mrbvInpA 		to "{P}{M}:MRBV.INPA";
int sPeriod;					assign sPeriod 			to "{P}{M}:SPERIOD";
double tGather;					assign tGather			to "{P}{M}:TGATHER";
double fSample;					assign fSample			to "{P}{M}:FSAMPLE";
double tSample;					assign tSample			to "{P}{M}:TSAMPLE";
string stateMsg;				assign stateMsg			to "{P}{M}:STATE.VAL";
string axisNoInAA;				assign axisNoInAA		to "{P}{M}:AXISNO.INAA";
string axisNoSval;				assign axisNoSval		to "{P}{M}:AXISNO.SVAL";
int    axisNoProc;				assign axisNoProc		to "{P}{M}:AXISNO.PROC";
string calcTimeInpA;			assign calcTimeInpA		to "{P}{M}:CALCTIME.INPA";
string calcTimeInpB;			assign calcTimeInpB		to "{P}{M}:CALCTIME.INPB";
string calcTimeInpC;			assign calcTimeInpC		to "{P}{M}:CALCTIME.INPC";
double calcTimeVal;				assign calcTimeVal		to "{P}{M}:CALCTIME.VAL";
int collecting;					assign collecting		to "{P}{M}:COLLECTING";
int parsing;					assign parsing			to "{P}{M}:PARSING";
int gathering;					assign gathering		to "{P}{M}:GATHERING";
string asynRec;					assign asynRec			to "{P}{M}:ASYNREC.VAL";

/* place holders for the asyn record
 * use either {P}{M}:ASYN or for testing BL16B-MO-IOC-02:asyn
 */
string asynIfmt;				assign asynIfmt			to "";
string asynAout;				assign asynAout			to "";
string asynAinp;				assign asynAinp			to "";
string asynPcnct;				assign asynPcnct		to "";
string asynPort;				assign asynPort			to "";
int asynNord;					assign asynNord			to "";
char asynBinp[MAX_RAW_CHARS];	assign asynBinp			to "";

double waveformRecs[MAX_N_DATASRC][N_ELEMENTS];
assign waveformRecs to {
	"{P}{M}:POSN",
	"{P}{M}:FERR",
	"{P}{M}:VELO"};

int axisNo;
int pmacNo;
double Ixx08;
double Ixx09;
double Ixx60;
double lenClkTick;
int I52;
int M72;
string tmpPvStr;

monitor execute;
monitor demandVal;
monitor motor;
monitor sPeriod;
monitor calcTimeVal;
monitor asynBinp;
monitor asynRec;
monitor asynPort;

evflag executeMon; 		sync execute 		executeMon;
evflag motorMon;	 	sync motor		 	motorMon;
evflag sPeriodMon; 		sync sPeriod		sPeriodMon;
evflag asynBinpMon;		sync asynBinp		asynBinpMon;
evflag asynRecMon;		sync asynRec		asynRecMon;
evflag asynPortMon;		sync asynPort		asynPortMon;

/* define exacaped C functions at end of the file. */
%{

int i;

unsigned int motorBaseAddr[33] = {0,	0x080, 0x100, 0x180, 0x200, 0x280, 0x300, 0x380, 0x400,
			  							0x480, 0x500, 0x580, 0x600, 0x680, 0x700, 0x780, 0x800,
			  							0x880, 0x900, 0x980, 0xA00, 0xA80, 0xB00, 0xB80, 0xC00,
			  							0xC80, 0xD00, 0xD80, 0xE00, 0xE80, 0xF00, 0xF80, 0x1000 };

typedef struct {
	unsigned int offset;
	char desc[80];
	unsigned int nBytesWide;
	unsigned int type;
	double scalingFactor;
	} dataSrcStruct_t;
/*
	 valid types are (according to Turbo SRM p.225):
	0x0: Y-register only 24 bits
	0x4: X-register only 24 bits
	0x8: X/Y double register 48 bits interpret as integer.
	0xC: X/Y double register 48 bits interpret as floating point.
*/
static dataSrcStruct_t dataSrc[MAX_N_DATASRC] = {
	{ 0x0B, "Actual position", 8, 0x8, 1 },					/* scaling: 1.0/( Ixx08 * 32.0 ) */
	{ 0x11, "Following error", 8, 0x8, 1 },					/* scaling: 1.0/( Ixx08 * 32.0 ) */
	{ 0x1D, "Actual unfiltered velocity", 4, 0x4, 1 },		/* scaling: 1.0/( Ixx09 * 32.0 )/( Ixx60 + 1 ) */ 
};

static int pu_getAxisNo(char* motorOutField);
static int pu_parseRawData(struct UserVar *pVar);

}%

ss ssGather 
{
	state INIT 
	{
		entry
		{
			printf("ssGather: ### state INIT entry. ###\n");
			strcpy(stateMsg, "INIT");
			pvPut(stateMsg, SYNC);
		}
		when()
		{
			printf("ssGather: clearing all event flags.\n");
			efClear(executeMon);
			efClear(motorMon);
			efClear(sPeriodMon);
			axisNo = 0;
			collecting = 0;
			pvPut(collecting, SYNC);
			parsing = 0;
			pvPut(parsing, SYNC);
			gathering = 0;
			pvPut(gathering, SYNC);
		} state CONNECT_ASYN
	}
	
	state CONNECT_ASYN
	{
		entry
		{
			printf("ssGather: ### state CONNECT_ASYN entry.\n");
			strcpy(stateMsg, "CONNECT_ASYN");
			pvPut(stateMsg, SYNC);
		
			printf("ssGather: asynRec currently: %s\n", asynRec);
		}
		
		when( efTestAndClear( asynRecMon ) && strlen( asynRec ) > 1 )
		{
			sprintf(tmpPvStr, "%s.PORT", asynRec);
			printf("ssGather: assigning %s\n", tmpPvStr);
			pvAssign(asynPort, tmpPvStr);
			
			sprintf(tmpPvStr, "%s.IFMT", asynRec);
			printf("ssGather: assigning %s\n", tmpPvStr);
			pvAssign(asynIfmt , tmpPvStr);
			
			sprintf(tmpPvStr, "%s.AOUT", asynRec);
			printf("ssGather: assigning %s\n", tmpPvStr);
			pvAssign(asynAout , tmpPvStr);
			
			sprintf(tmpPvStr, "%s.AINP", asynRec);
			printf("ssGather: assigning %s\n", tmpPvStr);
			pvAssign(asynAinp , tmpPvStr);
			
			sprintf(tmpPvStr, "%s.NORD", asynRec);
			printf("ssGather: assigning %s\n", tmpPvStr);
			pvAssign(asynNord , tmpPvStr);
			
			sprintf(tmpPvStr, "%s.PCNCT", asynRec);
			printf("ssGather: assigning %s\n", tmpPvStr);
			pvAssign(asynPcnct, tmpPvStr);
			
			sprintf(tmpPvStr, "%s.BINP", asynRec);
			printf("ssGather: assigning %s\n", tmpPvStr);
			pvAssign(asynBinp , tmpPvStr);
			
			pvMonitor(asynBinp);
			pvMonitor(asynPort);
		} state CONNECT_ASYN
		
		when( pvConnectCount() == pvChannelCount() )
		{
			printf("ssGather: all channels finally connected...\n");
			pvGet(asynPcnct, SYNC);
			if (strcmp(asynPcnct, "Connect") != 0) printf("ssGather: WARNING asyn record %s is not connected!\n", asynRec);

			/* ensure that the asyn record is in ASCII mode */
			printf("sending IFMT=ASCII\n");
			strcpy(asynIfmt, "ASCII");
			pvPut(asynIfmt);
		} state GET_SAMPLING_SETTINGS
		
	}
	
	state GET_SAMPLING_SETTINGS
	{
		entry
		{
			printf("ssGather: ### state GET_SAMPLING_SETTINGS entry. ###\n");
			strcpy(stateMsg, "GET_SAMPLING_SETTINGS");
			pvPut(stateMsg, SYNC);
		
		}
		
		when( )
		{
			/* Get the sample time settings from this new PMAC */
			strcpy(asynAout, "M72->Y:$000037,0,24 M72 I52");
			pvPut(asynAout, SYNC);
			pvGet(asynAinp);
			sscanf(asynAinp, "%d\r%d", &M72, &I52);
			printf("ssGather: I52=%d M72=%d\n", I52, M72);
			
			strcpy(asynAout, "I5049");
			pvPut(asynAout, SYNC);
			pvGet(asynAinp, SYNC);
			sscanf(asynAinp, "%d", &sPeriod);
			pvPut(sPeriod, SYNC);
			efClear(sPeriodMon);
			

		} state CALC_SAMPLING_SETTINGS
	}

	state CALC_SAMPLING_SETTINGS
	{
		entry
		{
			printf("ssGather: ### state CALC_SAMPLING_SETTINGS entry. ###\n");
			strcpy(stateMsg, "CALC_SAMPLING_SETTINGS");
			pvPut(stateMsg, SYNC);
		}
		when()
		{
			/* calculate sample time, frequency and gathering time */
			lenClkTick = 203.4/(I52 + 1);
			tSample = sPeriod * lenClkTick * M72/1000000.0; /* milliseconds */
			pvPut(tSample);
			fSample = 1.0/tSample; /* kHz */
			pvPut(fSample);
			tGather = N_ELEMENTS * tSample / 1000.0; /* seconds */
			pvPut(tGather);
			printf("ssGather: tSample=%fms fSample=%fkHz gather time: %fs\n", tSample, fSample, tGather);
		} state MONITOR_INPUT
	}
	
	state MONITOR_INPUT
	{
		entry
		{
			printf("ssGather: ### state MONITOR_INPUT ###\n");
			strcpy(stateMsg, "MONITOR_INPUT");
			pvPut(stateMsg, SYNC);
		}
		
		when( efTestAndClear(executeMon) && (execute == 1) )
		{
			printf("ssGather: got execute trigger from user.\n");
		} state SETUP
		
		when( efTestAndClear(sPeriodMon) )
		{
		} state CALC_SAMPLING_SETTINGS
		
		when (efTestAndClear( asynPortMon ))
		{
		} state GET_SAMPLING_SETTINGS
		
		when( efTest( asynRecMon ))
		{
		} state CONNECT_ASYN

		when( efTestAndClear(motorMon) )
		{
			sprintf(moveOut, "%s.VAL CA", motor);
			printf("ssGather: moveOut = %s\n", moveOut);
			pvPut(moveOut);
			sprintf(mrbvInpA, "%s.RBV CPP", motor);
			printf("ssGather: mrbvInpA = %s\n", mrbvInpA);
			pvPut(mrbvInpA);
			sprintf(axisNoInAA, "%s.OUT CA", motor);
			printf("ssGather: axisNoInAA = %s\n", axisNoInAA);
			pvPut(axisNoInAA);
			sprintf(calcTimeInpA, "%s.RBV NPP NMS", motor);
			printf("ssGather: calcTiemInpA = %s\n", calcTimeInpA);
			pvPut(calcTimeInpA);
			sprintf(calcTimeInpB, "%s.VELO NPP NMS", motor);
			printf("ssGather: calcTiemInpB = %s\n", calcTimeInpB);
			pvPut(calcTimeInpB);
			sprintf(calcTimeInpC, "%s.ACCL NPP NMS", motor);
			printf("ssGather: calcTiemInpC = %s\n", calcTimeInpC);
			pvPut(calcTimeInpC);
			} state MONITOR_INPUT
	}
	
	state SETUP
	{
		entry
		{
			printf("ssGather: ### state SETUP ###\n");
			strcpy(stateMsg, "SETUP");
			pvPut(stateMsg);
			axisNoProc = 1;
			pvPut(axisNoProc);
			pvGet(axisNoSval);
			sscanf(axisNoSval, "@asyn(pmac%d,%d)", &pmacNo, &axisNo);
			printf("ssGather: got axis no: %d (%s)\n", axisNo, axisNoSval);
		}
		when( axisNo < 1 || axisNo > 32)
		{
			printf("ssGather: invalid axis no:  %d [1..32]\n", axisNo);
		} state MONITOR_INPUT
		
		when()
		{
			printf("ssGather: getting scaling ivars...\n");
			
			sprintf(asynAout, "i%d08", axisNo);
			pvPut(asynAout, SYNC);
			pvGet(asynAinp);
			sscanf(asynAinp, "%lf", &Ixx08);
			printf("ssGather: %s = %f\n", asynAout, Ixx08);

			sprintf(asynAout, "i%d09", axisNo);
			pvPut(asynAout, SYNC);
			pvGet(asynAinp);
			sscanf(asynAinp, "%lf", &Ixx09);
			printf("ssGather: %s = %.3f\n", asynAout, Ixx09);
		
			sprintf(asynAout, "i%d60", axisNo);
			pvPut(asynAout, SYNC);
			pvGet(asynAinp);
			sscanf(asynAinp, "%lf", &Ixx60);
			printf("ssGather: %s = %f\n", asynAout, Ixx60);
			
			printf("ssGather: calculating the scaling factors...\n");
			if( Ixx08 != 0.0) dataSrc[0].scalingFactor = 1.0/(Ixx08 * 32.0);
			printf("ssGather: actual position factor = %f\n", dataSrc[0].scalingFactor);
			
			if( Ixx08 != 0.0) dataSrc[1].scalingFactor = 1.0/(Ixx08 * 32.0);
			printf("ssGather: following error factor = %f\n", dataSrc[1].scalingFactor);

			if (Ixx09 != 0.0 && Ixx60 != -1.0) 
				dataSrc[2].scalingFactor = 1.0/(Ixx09 * 32.0)/(Ixx60 + 1);
			printf("ssGather: actual velocity factor = %f\n", dataSrc[2].scalingFactor);
			
			printf("ssGather: setting up all ivars for gathering...\n");
			/* i5050, i5051: select gather channels.
			   i5001..3: gather channels - contain the data src address.
			   i5049: sample period in servo cycles.
			 */
			strcpy(asynAout, "i5050=7 i5051=0");
			pvPut(asynAout, SYNC);
			sprintf(asynAout, "i5049=%d", sPeriod);
			pvPut(asynAout, SYNC);
			
			sprintf(asynAout, "i5001=$%X%05X", dataSrc[0].type, dataSrc[0].offset + motorBaseAddr[axisNo] );
			pvPut(asynAout, SYNC);
			sprintf(asynAout, "i5002=$%X%05X", dataSrc[1].type, dataSrc[1].offset + motorBaseAddr[axisNo] );
			pvPut(asynAout, SYNC);
			sprintf(asynAout, "i5003=$%X%05X", dataSrc[2].type, dataSrc[2].offset + motorBaseAddr[axisNo] );
			pvPut(asynAout, SYNC);

			printf("ssGather: sending define gather cmd...\n");
			sprintf(asynAout, "define gather %d", 47 + (MAX_N_DATASRC * N_ELEMENTS));
			pvPut(asynAout);
			printf("ssGather: sent out: %s\n", asynAout);
			
		} state GATHER
	}

	state GATHER
	{
		entry
		{
			printf("ssGather: ### state GATHER ###\n");
			strcpy(stateMsg, "GATHER");
			pvPut(stateMsg);
			gathering = 1;
			pvPut(gathering, SYNC);
			
			printf("ssGather: sending gather command to trigger gathering\n");
			strcpy(asynAout, "gather");
			pvPut(asynAout);
			
			printf("ssGather: sending demand command to motor to start moving.\n");
			moveVal = demandVal;
			pvPut(moveVal);
		}
		when(delay(tGather + 0.5))
		{
			printf("ssGather: timeout - gathering must have stopped now...(I guess)\n");
			gathering = 0;
			pvPut(gathering, SYNC);
		} state COLLECT
	}

	state COLLECT
	{
		entry
		{
			printf("ssGather: ### state COLLECT ###\n");
			strcpy(stateMsg, "COLLECT");
			pvPut(stateMsg);
			
			/* only for testing!!! */
			printf("ssGather: sending IFMT=Hybrid\n");
			strcpy(asynIfmt, "Hybrid");
			pvPut(asynIfmt);
			
			printf("ssGather: sending list gather cmd to collect data from PMAC.\n");
			collecting = 1;
			pvPut(collecting, SYNC);
			strcpy(asynAout, "list gather");
			pvPut(asynAout, ASYNC);
		}
/*		when( efTestAndClear(asynBinpMon) )*/
		when( pvPutComplete(asynAout) && efTestAndClear(asynBinpMon))
		{
/*			pvGet(asynBinp);*/
			pvGet(asynBinp, SYNC);
			printf("ssGather: rawdata: \n" );
			%%for(i = 0; i < 16; i++) printf("%d:%d ", i, (int)pVar->asynBinp[i]);
			pvGet(asynNord, SYNC);
			printf("\nssGather: got raw data: %d ASCII chars!\n", asynNord);
		} state PARSE
		
		when( delay(10.0))
		{
			printf("ssGather: timeout - got tired of waiting for data from list gather.\n");
		} state PARSE
		exit
		{
			collecting = 0;
			pvPut(collecting, SYNC);
		}
	}

	state PARSE
	{
		entry
		{
			printf("ssGather: ### state PARSE ###\n");
			strcpy(stateMsg, "PARSE");
			pvPut(stateMsg);
			parsing = 1;
			pvPut(parsing, SYNC);
		}
		when()
		{
			printf("ssGather: parsing the raw ASCII data...\n");
			%%pu_parseRawData( pVar );
			printf("ssGather: posting the parsed data to the waveform records.\n");
			pvPut(waveformRecs[0], SYNC);
			pvPut(waveformRecs[1], SYNC);
			pvPut(waveformRecs[2], SYNC);
		} state MONITOR_INPUT
		exit
		{
			printf("ssGather: all done!\n");
			parsing = 0;
			pvPut(parsing, SYNC);
			execute = 0;
			pvPut(execute);
			efClear(executeMon);
		}
	}
}

/* C functions */
%{
int pu_getAxisNo(char* motorOutField)
{
	int pmacNo = 0;
	int axisNo = 0;
	int retval;
	printf("pu_getAxisNo: got string: \"%s\"\n", motorOutField);
	retval = sscanf(motorOutField, "@asyn(pmac%d,%d)", &pmacNo, &axisNo);
	printf("pu_getAxisNo: sscan returned: %d. PMAC: %d AXIS: %d\n", retval, pmacNo, axisNo);
	return axisNo;
}

static int pu_parseRawData(struct UserVar *pVar)
{
	int i, ret=0, dataSrcCounter = 3;
	unsigned int sampleCounter = 0;
	unsigned int charCounter = 0;
	int MSBY, LSBX;
	double scaling;
	char *substr1;
	char *substr2;
	char *substr3;
	
	substr1 = calloc(13, sizeof(char));
	substr2 = calloc(13, sizeof(char));
	substr3 = calloc(13, sizeof(char));
	
	printf("pu_parseRawData: nChars = %d\n", pVar->asynNord);
	
	for(	i = 0, sampleCounter = 0, dataSrcCounter = 0; 
			i < (N_ELEMENTS * MAX_N_DATASRC) && charCounter < (pVar->asynNord - 13);
			i++, charCounter += 13, dataSrcCounter++)
	{
		if (dataSrcCounter == MAX_N_DATASRC)
		{
			strncpy(substr1, (char*)(pVar->asynBinp + charCounter), 12);
			strncpy(substr2, (char*)(pVar->asynBinp + charCounter + 13), 12);
			strncpy(substr3, (char*)(pVar->asynBinp + charCounter + 26), 12);
			printf("-- %s %s %s --\n", substr1, substr2, substr3);
			dataSrcCounter = 0;
			sampleCounter++;
		}

		if (sscanf( (char*)(pVar->asynBinp + charCounter), "%06X%06X", &MSBY, &LSBX) != 2)
		{
			printf(	"pu_parseRawData: failed sscanf... returned: %d iteration: %d charCounter=%d sampleCounter=%d\n", 
					ret, i, charCounter, sampleCounter);
			printf("pu_parseRawData: rest of string: %s\n", (char*)(pVar->asynBinp + charCounter));
			break;
		}
		
		scaling = dataSrc[dataSrcCounter].scalingFactor;
		switch ( dataSrc[dataSrcCounter].type )
		{
			case 0x0:
				pVar->waveformRecs[dataSrcCounter][sampleCounter] = ((signed int)MSBY) * scaling;
				break;
			case 0x4:
				pVar->waveformRecs[dataSrcCounter][sampleCounter] = ((signed int)LSBX) * scaling;
				break;
			case 0x8:
				pVar->waveformRecs[dataSrcCounter][sampleCounter] = ((long int)((MSBY << 24) | LSBX)) * scaling;
				break;
			case 0xC:
				pVar->waveformRecs[dataSrcCounter][sampleCounter] = ((double)((MSBY << 24) | LSBX)) * scaling;
				break;
			default:
				printf("pu_parseRawData: this should not happen!\n");
				pVar->waveformRecs[dataSrcCounter][sampleCounter] = 0.0;
				break;
		}
		printf(	"pu_parseRawData: ch: %d MSB=0x%X LSB=0x%X scaled=%.3f\n",
				dataSrcCounter, MSBY, LSBX, pVar->waveformRecs[dataSrcCounter][sampleCounter]);
	}
	printf("pu_parseRawData: iterations=%d sampleCounter=%d\n", i, sampleCounter);
	return 0;
}

}%
