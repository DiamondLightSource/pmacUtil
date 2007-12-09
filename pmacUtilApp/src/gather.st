program gather("P=P,R=:M")

%%#include <stdio.h>
%%#include <stdlib.h>
%%#include <string.h>
option +r;
/* number of raw chars to receive from gathering 
   = 3 data sources x 1024 samples x (12 hex-chars + 1 lineend) + 2 end of stream chars
   = 39938 chars */
#define MAX_RAW_CHARS 39938
#define N_ELEMENTS 1024
#define MAX_N_DATASRC 3

int execute; 					assign execute 			to "{P}{M}:EXECUTE.VAL";
string motorRecord;				assign motorRecord 		to "{P}{M}:MOTOR";
string moveOut; 				assign moveOut 			to "{P}{M}:MOVE.OUT";
double moveVal; 				assign moveVal 			to "{P}{M}:MOVE.VAL";
double demandVal; 				assign demandVal 		to "{P}{M}:DEMAND.VAL";
string rbvInpa; 				assign rbvInpa 			to "{P}{M}:MRBV.INPA";
int samplePeriod;				assign samplePeriod 	to "{P}{M}:SPERIOD";
double Tgather;					assign Tgather			to "{P}{M}:TGATHER";
double Fsample;					assign Fsample			to "{P}{M}:FSAMPLE";
double Tsample;					assign Tsample			to "{P}{M}:TSAMPLE";
string stateMsg; 				assign stateMsg 		to "{P}{M}:STATE.VAL";
string motorOutInp;				assign motorOutInp		to "{P}{M}:AXISNO.INAA";
string strAxisNo;				assign strAxisNo		to "{P}{M}:AXISNO.SVAL";
int AxisNoProc;					assign AxisNoProc		to "{P}{M}:AXISNO.PROC";
string calcTimeInpA;			assign calcTimeInpA		to "{P}{M}:CALCTIME.INPA";
string calcTimeInpB;			assign calcTimeInpB		to "{P}{M}:CALCTIME.INPB";
string calcTimeInpC;			assign calcTimeInpC		to "{P}{M}:CALCTIME.INPC";
double moveTime;				assign moveTime			to "{P}{M}:CALCTIME.VAL";
int collecting;					assign collecting		to "{P}{M}:COLLECTING";
int parsing;					assign parsing			to "{P}{M}:PARSING";
int gathering;					assign gathering		to "{P}{M}:GATHERING";

/*string asynSetupAout;			assign asynSetupAout	to "{P}{M}:SETUP.AOUT";*/
string asynSetupAout;			assign asynSetupAout	to "BL16B-MO-IOC-02:asyn.AOUT";
/*string asynSetupAin;			assign asynSetupAin		to "{P}{M}:SETUP.AINP";*/
string asynSetupAin;			assign asynSetupAin		to "BL16B-MO-IOC-02:asyn.AINP";

string asynGetDataIfmt;			assign asynGetDataIfmt	to "BL16B-MO-IOC-02:asyn.IFMT";
/*string listGatherCmd;			assign listGatherCmd	to "{P}{M}:GETDATA.AOUT";*/
string listGatherCmd;			assign listGatherCmd	to "BL16B-MO-IOC-02:asyn.AOUT";
/*int nRawChars; 				assign nRawChars 		to "{P}{M}:GETDATA.NORD";*/
int nRawChars; 					assign nRawChars 		to "BL16B-MO-IOC-02:asyn.NORD";
/*char rawData[MAX_RAW_CHARS]; 	assign rawData 			to "{P}{M}:GETDATA.BINP";*/
char rawData[MAX_RAW_CHARS]; 	assign rawData 			to "BL16B-MO-IOC-02:asyn.BINP";

/*string asynPmacTrigAout;		assign asynPmacTrigAout	to "{P}{M}:PMACTRIG.AOUT";*/
string asynPmacTrigAout;		assign asynPmacTrigAout	to "BL16B-MO-IOC-02:asyn.AOUT";

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

monitor execute;
monitor demandVal;
monitor motorRecord;
monitor samplePeriod;
monitor moveTime;
monitor rawData;

evflag executeMon; 		sync execute 			executeMon;
evflag motorRecordMon; 	sync motorRecord 		motorRecordMon;
evflag samplePeriodMon; sync samplePeriod		samplePeriodMon;
evflag rawDataMon;		sync rawData			rawDataMon;

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
	 valid types are (according to Turbo SRM p.225:
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

static int getAxisNo(char* motorOutField);
static int parseRawData(struct UserVar *pVar);

}%

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
			efClear(motorRecordMon);
			efClear(samplePeriodMon);
			axisNo = 0;
			collecting = 0;
			pvPut(collecting, SYNC);
			parsing = 0;
			pvPut(parsing, SYNC);
			gathering = 0;
			pvPut(gathering, SYNC);
		} state MONITOR_INPUT
	}

	state MONITOR_INPUT
	{
		entry
		{
			printf("ssGather: state MONITOR_INPUT\n");
			strcpy(stateMsg, "MONITOR_INPUT");
			pvPut(stateMsg);

			/* only for testing!!! */
			printf("sending IFMT=ASCII\n");
			strcpy(asynGetDataIfmt, "ASCII");
			pvPut(asynGetDataIfmt);
		}
		when( efTestAndClear(executeMon) && (execute == 1) )
		{
			printf("ssGather: got execute trigger from user.\n");
		} state SETUP

		when( efTestAndClear(motorRecordMon) )
		{
			sprintf(moveOut, "%s.VAL CA", motorRecord);
			printf("ssGather: moveOut = %s\n", moveOut);
			pvPut(moveOut);
			sprintf(rbvInpa, "%s.RBV CPP", motorRecord);
			printf("ssGather: rbvInpa = %s\n", rbvInpa);
			pvPut(rbvInpa);
			sprintf(motorOutInp, "%s.OUT CA", motorRecord);
			printf("ssGather: motorOutInp = %s\n", motorOutInp);
			pvPut(motorOutInp);
			sprintf(calcTimeInpA, "%s.RBV NPP NMS", motorRecord);
			printf("ssGather: calcTiemInpA = %s\n", calcTimeInpA);
			pvPut(calcTimeInpA);
			sprintf(calcTimeInpB, "%s.VELO NPP NMS", motorRecord);
			printf("ssGather: calcTiemInpB = %s\n", calcTimeInpB);
			pvPut(calcTimeInpB);
			sprintf(calcTimeInpC, "%s.ACCL NPP NMS", motorRecord);
			printf("ssGather: calcTiemInpC = %s\n", calcTimeInpC);
			pvPut(calcTimeInpC);
			} state MONITOR_INPUT

		when( efTestAndClear(samplePeriodMon) )
		{
			/* calculate the sample and sampling time */
			strcpy(asynSetupAout, "M72->Y:$000037,0,24 M72 I52");
			pvPut(asynSetupAout, SYNC);
			pvGet(asynSetupAin);
			sscanf(asynSetupAin, "%d\r%d", &M72, &I52);
			printf("ssGather: I52=%d M72=%d\n", I52, M72);
			lenClkTick = 203.4/(I52 + 1);
			Tsample = samplePeriod * lenClkTick * M72/1000000.0; /* milliseconds */
			pvPut(Tsample);
			Fsample = 1.0/Tsample; /* kHz */
			pvPut(Fsample);
			Tgather = N_ELEMENTS * Tsample / 1000.0; /* seconds */
			pvPut(Tgather);
			printf("ssGather: Tsample=%lfms Fsample=%lfkHz gather time: %lfs\n", Tsample, Fsample, Tgather);
		} state MONITOR_INPUT
	}
	
	state SETUP
	{
		entry
		{
			printf("ssGather: state SETUP\n");
			strcpy(stateMsg, "SETUP");
			pvPut(stateMsg);
			AxisNoProc = 1;
			pvPut(AxisNoProc);
			pvGet(strAxisNo);
			sscanf(strAxisNo, "@asyn(pmac%d,%d)", &pmacNo, &axisNo);
			printf("ssGather: got axis no: %d (%s)\n", axisNo, strAxisNo);
		}
		when( axisNo < 1 || axisNo > 32)
		{
			printf("ssGather: invalid axis no:  %d [1..32]\n", axisNo);
		} state MONITOR_INPUT
		when()
		{
			printf("ssGather: getting scaling ivars...\n");
			
			sprintf(asynSetupAout, "i%d08", axisNo);
			pvPut(asynSetupAout, SYNC);
			pvGet(asynSetupAin);
			sscanf(asynSetupAin, "%lf", &Ixx08);
			printf("ssGather: %s = %lf\n", asynSetupAout, Ixx08);

			sprintf(asynSetupAout, "i%d09", axisNo);
			pvPut(asynSetupAout, SYNC);
			pvGet(asynSetupAin);
			sscanf(asynSetupAin, "%lf", &Ixx09);
			printf("ssGather: %s = %lf\n", asynSetupAout, Ixx09);
		
			sprintf(asynSetupAout, "i%d60", axisNo);
			pvPut(asynSetupAout, SYNC);
			pvGet(asynSetupAin);
			sscanf(asynSetupAin, "%lf", &Ixx60);
			printf("ssGather: %s = %lf\n", asynSetupAout, Ixx60);
			
			printf("ssGather: calculating the scaling factors...\n");
			if( Ixx08 != 0.0) dataSrc[0].scalingFactor = 1.0/(Ixx08 * 32.0);
			printf("ssGather: actual position factor = %lf\n", dataSrc[0].scalingFactor);
			
			if( Ixx08 != 0.0) dataSrc[1].scalingFactor = 1.0/(Ixx08 * 32.0);
			printf("ssGather: following error factor = %lf\n", dataSrc[1].scalingFactor);

			if (Ixx09 != 0.0 && Ixx60 != -1.0) 
				dataSrc[2].scalingFactor = 1.0/(Ixx09 * 32.0)/(Ixx60 + 1);
			printf("ssGather: actual velocity factor = %lf\n", dataSrc[2].scalingFactor);
			
			printf("ssGather: setting up all ivars for gathering...\n");
			/* i5050, i5051: select gather channels.
			   i5001..3: gather channels - contain the data src address.
			   i5049: sample period in servo cycles.
			 */
			strcpy(asynSetupAout, "i5050=7 i5051=0");
			pvPut(asynSetupAout, SYNC);
			sprintf(asynSetupAout, "i5049=%d", samplePeriod);
			pvPut(asynSetupAout, SYNC);
			
			sprintf(asynSetupAout, "i5001=$%X%05X", dataSrc[0].type, dataSrc[0].offset + motorBaseAddr[axisNo] );
			pvPut(asynSetupAout, SYNC);
			sprintf(asynSetupAout, "i5002=$%X%05X", dataSrc[1].type, dataSrc[1].offset + motorBaseAddr[axisNo] );
			pvPut(asynSetupAout, SYNC);
			sprintf(asynSetupAout, "i5003=$%X%05X", dataSrc[2].type, dataSrc[2].offset + motorBaseAddr[axisNo] );
			pvPut(asynSetupAout, SYNC);

			printf("ssGather: sending define gather cmd...\n");
			sprintf(asynSetupAout, "define gather %d", 47 + (MAX_N_DATASRC * N_ELEMENTS));
			pvPut(asynSetupAout);
			printf("ssGather: sent out: %s\n", asynSetupAout);
			
		} state GATHER
	}

	state GATHER
	{
		entry
		{
			printf("ssGather: state GATHER\n");
			strcpy(stateMsg, "GATHER");
			pvPut(stateMsg);
			gathering = 1;
			pvPut(gathering, SYNC);
			
			printf("ssGather: sending gather command to trigger gathering\n");
			strcpy(asynPmacTrigAout, "gather");
			pvPut(asynPmacTrigAout);
			
			printf("ssGather: sending demand command to motor to start moving.\n");
			moveVal = demandVal;
			pvPut(moveVal);
		}
		when(delay(Tgather + 0.5))
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
			printf("ssGather: state COLLECT\n");
			strcpy(stateMsg, "COLLECT");
			pvPut(stateMsg);
			
			/* only for testing!!! */
			printf("sending IFMT=Hybrid\n");
			strcpy(asynGetDataIfmt, "Hybrid");
			pvPut(asynGetDataIfmt);
			
			printf("ssGather: sending list gather cmd to collect data from PMAC.\n");
			collecting = 1;
			pvPut(collecting, SYNC);
			strcpy(listGatherCmd, "list gather");
			pvPut(listGatherCmd, ASYNC);
		}
/*		when( efTestAndClear(rawDataMon) )*/
		when( pvPutComplete(listGatherCmd) && efTestAndClear(rawDataMon))
		{
			pvGet(nRawChars);
/*			pvGet(rawData, SYNC);*/
			printf("ssGather: rawdata: \n" );
			%%for(i = 0; i < 16; i++) printf("%d:%d ", i, (int)pVar->rawData[i]);
			printf("\nssGather: got raw data: %d ASCII chars!\n", nRawChars);
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
			printf("ssGather: state PARSE\n");
			strcpy(stateMsg, "PARSE");
			pvPut(stateMsg);
			parsing = 1;
			pvPut(parsing, SYNC);
		}
		when()
		{
			printf("ssGather: parsing the raw ASCII data...\n");
			%%parseRawData( pVar );
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
int getAxisNo(char* motorOutField)
{
	int pmacNo = 0;
	int axisNo = 0;
	int retval;
	printf("getAxisNo: got string: \"%s\"\n", motorOutField);
	retval = sscanf(motorOutField, "@asyn(pmac%d,%d)", &pmacNo, &axisNo);
	printf("getAxisNo: sscan returned: %d. PMAC: %d AXIS: %d\n", retval, pmacNo, axisNo);
	return axisNo;
}

static int parseRawData(struct UserVar *pVar)
{
	int i, ret, dataSrcCounter = 3;
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
	
	printf("parseRawData: nChars = %d\n", pVar->nRawChars);
	
	for(	i = 0, sampleCounter = 0, dataSrcCounter = 0; 
			i < (N_ELEMENTS * MAX_N_DATASRC) && charCounter < (pVar->nRawChars - 13);
			i++, charCounter += 13, dataSrcCounter++)
	{
		if (dataSrcCounter == MAX_N_DATASRC)
		{
			strncpy(substr1, (char*)(pVar->rawData + charCounter), 12);
			strncpy(substr2, (char*)(pVar->rawData + charCounter + 13), 12);
			strncpy(substr3, (char*)(pVar->rawData + charCounter + 26), 12);
			printf("-- %s %s %s --\n", substr1, substr2, substr3);
			dataSrcCounter = 0;
			sampleCounter++;
		}

		if (sscanf( (char*)(pVar->rawData + charCounter), "%06X%06X", &MSBY, &LSBX) != 2)
		{
			printf(	"parseRawData: failed sscanf... returned: %d iteration: %d charCounter=%d sampleCounter=%d\n", 
					ret, i, charCounter, sampleCounter);
			printf("parseRawData: rest of string: %s\n", (char*)(pVar->rawData + charCounter));
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
				printf("parseRawData: this should not happen!\n");
				pVar->waveformRecs[dataSrcCounter][sampleCounter] = 0.0;
				break;
		}
		printf(	"parseRawData: ch: %d MSB=0x%X LSB=0x%X scaled=%lf\n",
				dataSrcCounter, MSBY, LSBX, pVar->waveformRecs[dataSrcCounter][sampleCounter]);
	}
	printf("parseRawData: iterations=%d sampleCounter=%d\n", i, sampleCounter);
	return 0;
}

}%
