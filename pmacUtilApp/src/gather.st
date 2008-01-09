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
#define SIZE_DOUBLE 8

int execute; 					assign execute 			to "{P}{M}:EXECUTE.VAL";
string motor;					assign motor	 		to "{P}{M}:MOTOR";
string moveOut; 				assign moveOut 			to "{P}{M}:MOVE.OUT";
double moveVal; 				assign moveVal 			to "{P}{M}:MOVE.VAL";
double demandVal; 				assign demandVal 		to "{P}{M}:DEMAND.VAL";
string mrbvInpA; 				assign mrbvInpA 		to "{P}{M}:MRBV.INPA";
int sPeriod;					assign sPeriod 			to "{P}{M}:SPERIOD";
double tGather;					assign tGather			to "{P}{M}:TGATHER";
double tSample;					assign tSample			to "{P}{M}:TSAMPLE";
double tSampleB;				assign tSampleB			to "{P}{M}:TSAMPLE.B";
double tSampleC;				assign tSampleC			to "{P}{M}:TSAMPLE.C";
string stateMsg;				assign stateMsg			to "{P}{M}:STATE.VAL";
int axisNo;						assign axisNo			to "{P}{M}:AXISNO";
int pmacNo;						assign pmacNo			to "{P}{M}:PMACNO";
string moveTimeInpB;			assign moveTimeInpB		to "{P}{M}:MOVETIME.INPB";
string moveTimeInpC;			assign moveTimeInpC		to "{P}{M}:MOVETIME.INPC";
double moveTimeVal;				assign moveTimeVal		to "{P}{M}:MOVETIME.VAL";
int collecting;					assign collecting		to "{P}{M}:COLLECTING";
int parsing;					assign parsing			to "{P}{M}:PARSING";
int gathering;					assign gathering		to "{P}{M}:GATHERING";
string movingInpA;				assign movingInpA		to "{P}{M}:MOVING.INPA";
double timeRec[N_ELEMENTS];		assign timeRec			to "{P}{M}:TIME";
string asynRec;					assign asynRec			to "{P}{M}:ASYNREC.VAL";
string port;					assign port				to "{P}{M}:PORT.VAL";

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
string motorOut;				assign motorOut			to "";


double waveformRecs[MAX_N_DATASRC][N_ELEMENTS];
assign waveformRecs to {
	"{P}{M}:POSN",
	"{P}{M}:FERR",
	"{P}{M}:VELO"};

int c;
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
monitor moveTimeVal;
monitor asynBinp;
monitor asynRec;
monitor asynPort;
monitor port;
monitor tGather;

evflag executeMon; 		sync execute 		executeMon;
evflag motorMon;	 	sync motor		 	motorMon;
evflag asynBinpMon;		sync asynBinp		asynBinpMon;
evflag asynRecMon;		sync asynRec		asynRecMon;
evflag asynPortMon;		sync asynPort		asynPortMon;
evflag portMon;			sync port			portMon;

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
			efClear(portMon);
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
			/* dynamically reconnect to all the interesting 
			 * fields of the asyn record 
			 */
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
		
		/* wait for all dynamically assigned PVs to connect */
		when( 	pvConnected(asynPort) &&
				pvConnected(asynIfmt) && 
				pvConnected(asynAout) &&
				pvConnected(asynAinp) &&
				pvConnected(asynNord) &&
				pvConnected(asynPcnct) &&
				pvConnected(asynBinp))
		{
			printf("ssGather: all channels finally connected...\n");
			pvGet(asynPcnct, SYNC);
			if (strcmp(asynPcnct, "Connect") != 0) printf("ssGather: WARNING asyn record %s is not connected to a PMAC!\n", asynRec);

			/* ensure that the asyn record is in ASCII mode */
			printf("ssGather: sending IFMT=ASCII\n");
			strcpy(asynIfmt, "ASCII");
			pvPut(asynIfmt);
		} state CONNECT_PMAC
	}
	
	state CONNECT_PMAC
	{
		entry
		{
			printf("ssGather: ### state CONNECT_PMAC entry. ###\n");
			strcpy(stateMsg, "CONNECT_PMAC");
			pvPut(stateMsg, SYNC);
			
			if (efTestAndClear(portMon))
			{
				/* port changed in stringout record */
				strcpy(asynPort, port);
				pvPut(asynPort, SYNC);
			} else 
			{
				/* port changed directly on asyn record */
				strcpy(port, asynPort);
				pvPut(port, SYNC);
			}
			efClear(portMon);
			efClear(asynPortMon);
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
		} state MONITOR_INPUT
	}
	
	state CONNECT_MOTOR
	{
		entry
		{
			printf("ssGather: ### state CONNECT_MOTOR entry. ###\n");
			strcpy(stateMsg, "CONNECT_MOTOR");
			pvPut(stateMsg, SYNC);

			/* connect to the new motor records out field */
			sprintf(tmpPvStr, "%s.OUT", motor);
			printf("ssGather: assigning %s\n", tmpPvStr);
			pvAssign(motorOut, tmpPvStr);
		}
		when( pvConnected(motorOut) )
		{
			sprintf(moveOut, "%s.VAL CA", motor);
			printf("ssGather: moveOut = %s\n", moveOut);
			pvPut(moveOut);
			sprintf(mrbvInpA, "%s.RBV CPP", motor);
			printf("ssGather: mrbvInpA = %s\n", mrbvInpA);
			pvPut(mrbvInpA);
			sprintf(movingInpA, "%s.MOVN CPP", motor);
			printf("ssGather: movingInpA = %s\n", movingInpA);
			pvPut(movingInpA);
			sprintf(moveTimeInpB, "%s.VELO CA", motor);
			pvPut(moveTimeInpB);
			sprintf(moveTimeInpC, "%s.ACCL CA", motor);
			pvPut(moveTimeInpC);
			
			/* parse the PMAC number and axis number from the 
			   motor records OUT field. */
			pvGet(motorOut);
			sscanf(motorOut, "@asyn(pmac%d,%d)", &pmacNo, &axisNo);
			printf("ssGather: got axis no: %d PMAC no: %d\n", axisNo, pmacNo);
			pvPut(pmacNo);
			pvPut(axisNo);
			
			/* set I52 and M72 to the frequency calculation records here... */
			tSampleB = I52;
			pvPut(tSampleB);
			tSampleC = M72;
			pvPut(tSampleC);
		} state MONITOR_INPUT

		/* this doesn't get executed... need to find different place for it */
		when( axisNo < 1 || axisNo > 32)
		{
			printf("ssGather: invalid axis no:  %d [1..32]\n", axisNo);
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
		
		when (efTest( asynPortMon ) || efTest(portMon) )
		{
		} state CONNECT_PMAC
		
		when( efTest( asynRecMon ) )
		{
		} state CONNECT_ASYN

		when( efTestAndClear(motorMon) )
		{
		} state CONNECT_MOTOR
	}
	
	state SETUP
	{
		entry
		{
			printf("ssGather: ### state SETUP ###\n");
			strcpy(stateMsg, "SETUP");
			pvPut(stateMsg);
		}
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
			
			printf("ssGather: clearing out the current waveforms...\n");
			memset(waveformRecs[0], 0, SIZE_DOUBLE*N_ELEMENTS);
			memset(waveformRecs[1], 0, SIZE_DOUBLE*N_ELEMENTS);
			memset(waveformRecs[2], 0, SIZE_DOUBLE*N_ELEMENTS);
			pvPut(waveformRecs[0], SYNC);
			pvPut(waveformRecs[1], SYNC);
			pvPut(waveformRecs[2], SYNC);
			
			printf("ssGather: calculating the time axis\n");
			pvGet(tSample);
			for(c=0; c<N_ELEMENTS; c++) timeRec[c] = c * tSample;
			pvPut(timeRec, SYNC);

			printf("ssGather: sending endgather cmd to end any possible ongoing gathering.\n");
			sprintf(asynAout, "endgather");
			pvPut(asynAout, SYNC);
			
			printf("ssGather: sending delete gather cmd to clear any current buffer.\n");
			sprintf(asynAout, "delete gather");
			pvPut(asynAout, SYNC);

			printf("ssGather: sending define gather cmd...\n");
			sprintf(asynAout, "define gather %d", 47 + (MAX_N_DATASRC * N_ELEMENTS));
			pvPut(asynAout, SYNC);
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
			pvPut(asynAout, SYNC);
			
			printf("ssGather: sending demand command to motor to start moving.\n");
			moveVal = demandVal;
			pvPut(moveVal, SYNC);
			
			printf("ssGather: waiting for gathering to stop... (%.3f + 1.0s)\n", tGather );
		}
		when(delay(tGather + 1.0))
		{
			printf("ssGather: timeout - gathering must have stopped now...(after %.2fs gather + 1.0s)\n", tGather);
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
		when( pvPutComplete(asynAout) && efTestAndClear(asynBinpMon))
		{
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
			strcpy(asynIfmt, "ASCII");
			pvPut(asynIfmt);

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
	unsigned int MSBY, LSBX;
	double scaling;
	char *substr1;
	char *substr2;
	char *substr3;
	double tmpDouble;
	long long int *tmpPtr;
	long long int tmpLong;
	
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
			printf("-- %.3f %.3f %.3f --\n", 	pVar->waveformRecs[0][sampleCounter], 
												pVar->waveformRecs[1][sampleCounter],
												pVar->waveformRecs[2][sampleCounter]);
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
				/* get the 24bit Y word as a signed integer and fit it in a signed 32 bit word */
				if ((MSBY & 0x800000) > 0)
					pVar->waveformRecs[dataSrcCounter][sampleCounter] = ((signed int)(MSBY | 0xFF000000) * scaling);
				else
					pVar->waveformRecs[dataSrcCounter][sampleCounter] = ((signed int)MSBY) * scaling;					
				break;
			case 0x4:
				/* get the 24bit X word as a signed integer and fit it in a signed 32 bit word */
				if ((LSBX & 0x800000) > 0)
					pVar->waveformRecs[dataSrcCounter][sampleCounter] = ((signed int)(LSBX | 0xFF000000) * scaling);
				else
					pVar->waveformRecs[dataSrcCounter][sampleCounter] = ((signed int)LSBX) * scaling;									
				break;
			case 0x8:
				/* get the 48 bit word (X and Y) as a signed integer and fit it in a 64 bit word */
				tmpLong = ((long long int)MSBY << 24) | LSBX;
				if ((MSBY & 0x800000) > 0)
				{
					tmpLong = tmpLong | 0xFFFF000000000000;
					pVar->waveformRecs[dataSrcCounter][sampleCounter] = tmpLong * scaling;
				}
				else
					pVar->waveformRecs[dataSrcCounter][sampleCounter] = tmpLong * scaling;
				break;
			case 0xC:
				/* get the 48 bit word (X and Y) as a double precision floating point value
				   and fit it in a 64 bit double (as it uses 12 bit exponent it is simply a 16 bit shift) */
				tmpPtr = (long long int*)&tmpDouble;
				*tmpPtr = ((long long int)MSBY << 24) | LSBX;
				*tmpPtr = *tmpPtr << 16;
				pVar->waveformRecs[dataSrcCounter][sampleCounter] = tmpDouble * scaling;
				break;
			default:
				printf("pu_parseRawData: this should not happen!\n");
				pVar->waveformRecs[dataSrcCounter][sampleCounter] = 0.0;
				break;
		}
/*		printf(	"pu_parseRawData: ch: %d MSB=0x%X LSB=0x%X scaled=%.3f\n",
				dataSrcCounter, MSBY, LSBX, pVar->waveformRecs[dataSrcCounter][sampleCounter]);*/
	}
	printf("pu_parseRawData: iterations=%d sampleCounter=%d\n", i+1, sampleCounter+1);
	return 0;
}

}%
