
/*
 *	Programming Assignment 1 
 *	Name: Evan Rutherford (G01077323)
 *	Class: CS455 - 002
 */

#include<stdio.h>
#include<string.h>
#include<stdlib.h>
#include<sys/socket.h>	
#include<arpa/inet.h>
#include<netinet/in.h>
#include<unistd.h>	
#include<sys/time.h>

#define T_A 1 	//Ipv4 address
#define T_NS 2 	//Nameserver
#define T_CNAME 5 // canonical name
#define T_SOA 6 	/* start of authority zone */
#define T_PTR 12	 /* domain name pointer */

void DNSquerytoHost(unsigned char *host, int query_type);
void formatDNSname(unsigned char *dns,unsigned char *hostname);
unsigned char* readName(unsigned char *pointer,unsigned char *buffer,int *count);

//	DNS header structure
struct DNS_HEADER
{
	unsigned short id; 		// Identification number
	unsigned char rd :1; 	// Recursion desired
	unsigned char tc :1; 	// Truncated message
	unsigned char aa :1; 	// Authoritive answer
	unsigned char opcode :4; // Purpose of message
	unsigned char qr :1; 	// Query/Response flag
	unsigned char rcode :4; // Response code
	unsigned char cd :1; 	// Checking Disabled
	unsigned char ad :1; 	// Authenticated data
	unsigned char z :1; 	// Z reserved
	unsigned char ra :1; 	// Recursion available
	unsigned short q_count; // Number of question entries
	unsigned short ans_count; // Number of answer entries
	unsigned short auth_count; // Number of authority entries
	unsigned short add_count; // Number of resource entries
};

//	QUESTION query with qname separate from structure
struct QUESTION
{
	unsigned short qtype;
	unsigned short qclass;
};

//	Data for authority/additional resource
#pragma pack(push, 1)
struct R_DATA
{
	unsigned short type;
	unsigned short _class;
	unsigned int ttl;
	unsigned short data_len;
};
#pragma pack(pop)

//Pointers to authority/additional resources 
struct RES_RECORD
{
	unsigned char *name;
	struct R_DATA *resource;
	unsigned char *rdata;
};

int main( int argc , char *argv[])
{
	unsigned char hostname[20];
	
	if(argc == 2){
		sscanf(argv[1], "%s", hostname);
	}
	else{
		printf("command format: 'a.out' 'hostname'\n");
		exit(1);
	}

	if(hostname != NULL){
		DNSquerytoHost(hostname , 1);
	}

	return 0;
}

/*
 * Perform a DNS query by sending a packet
 * */
void DNSquerytoHost(unsigned char *host , int query_type)
{
	unsigned char buffer[10000],*qname,*pointer,*value;
	int i, j, stop, s, x;

	struct sockaddr_in a;
	struct sockaddr_in dest;

	struct DNS_HEADER *dns = NULL;
	struct QUESTION *qinfo = NULL;

	struct RES_RECORD answers[20],auth[20],addit[20]; 
	
	printf("---Resolving %s---" , host);

	printf("\nPreparing DNS query...");	
	dest.sin_family = AF_INET;
	dest.sin_port = htons(53);
	dest.sin_addr.s_addr = inet_addr("8.8.8.8");
	
	printf("\nContacting DNS server...");
	s = socket(AF_INET , SOCK_DGRAM , 0); 

	//	Set the DNS structure to HEADER query
	dns = (struct DNS_HEADER *)&buffer;

	dns->id = (unsigned short)htons(getpid());
	dns->qr = 0; 
	dns->opcode = 0; 
	dns->aa = 0;
	dns->tc = 0; 
	dns->rd = 1; 
	dns->ra = 0;
	dns->z = 0;
	dns->ad = 0;
	dns->cd = 0;
	dns->rcode = 0;
	dns->q_count = htons(1);
	dns->ans_count = 0;
	dns->auth_count = 0;
	dns->add_count = 0;

	//	Point qname to the beginning of the question section
	qname =(unsigned char*)&buffer[sizeof(struct DNS_HEADER)];

	formatDNSname(qname , host);
	
	qinfo =(struct QUESTION*)&buffer[sizeof(struct DNS_HEADER) + (strlen((const char*)qname) + 1)]; 	//Add QUESTION into buf/dns structure and add values
	qinfo->qtype = htons(1);
	qinfo->qclass = htons(1); 

	printf("\nSending DNS query...");
	x = 0;
	if( sendto(s,(char*)buffer,sizeof(struct DNS_HEADER) + (strlen((const char*)qname)+1) + sizeof(struct QUESTION),0,(struct sockaddr*)&dest,sizeof(dest)) < 0)
	{
		perror("sendto failed");
	}
	
	/*
 	* 	Receive the answer from the server and print values
 	*/
	i = sizeof dest;
	x = 1;
	struct timeval wait;
	wait.tv_sec = 5;
	wait.tv_usec = 0;
	for(x = 1;x<3;x++)
	{
		if(setsockopt(s, SOL_SOCKET, SO_RCVTIMEO, (char*)&wait, sizeof(wait)) < 0){
			//perror("timed out!\n");
		}
		if(recvfrom(s, (char*)buffer, 10000, 0, (struct sockaddr*)&dest, (socklen_t*)&i) < 0){
			//perror("recvfrom failed");
		}
	}
	printf("\nDNS response received (attempt %d of 3)",x);

	dns = (struct DNS_HEADER*) buffer;

	printf("\nProcessing DNS response...");
	printf("\n\nThe response contains : ");
	printf("\nQuestions: %d",ntohs(dns->q_count));
	printf("\nAnswers: %d",ntohs(dns->ans_count));
	printf("\nAuthorized Servers: %d",ntohs(dns->auth_count));
	printf("\nAdditional RRs: %d\n",ntohs(dns->add_count));
	printf("\n-----------------------------------------------------");
	printf("\nheader.ID = %d",ntohs(dns->id));
	printf("\nheader.QR = %d",ntohs(dns->q_count));
	printf("\nheader.OPCODE = %d",ntohs(dns->opcode));
	printf("\nheader.AA = %d",ntohs(dns->aa));
	printf("\nheader.TC = %d",ntohs(dns->tc));
	printf("\nheader.RD = %d",dns->rd);
	printf("\nheader.RA = %d",dns->ra);
	printf("\nheader.Z = %d",ntohs(dns->z));
	printf("\nheader.RCODE = %d",ntohs(dns->rcode));
	printf("\nheader.QDCOUNT = %d",ntohs(dns->q_count));
	printf("\nheader.ANCOUNT = %d",ntohs(dns->ans_count));
	printf("\nheader.NSCOUNT = %d",ntohs(dns->auth_count));
	printf("\nheader.ARCOUNT = %d",ntohs(dns->add_count));
	printf("\n-----------------------------------------------------");
	printf("\nquestion.QNAME = %s",qname);
	printf("\nquestion.QTYPE = %d",ntohs(qinfo->qtype));
	printf("\nquestion.QCLASS = %d",ntohs(qinfo->qtype));
	printf("\n-----------------------------------------------------");


	
	//	Move the dns pointer in front of the header and the question field
	pointer = &buffer[sizeof(struct DNS_HEADER) + (strlen((const char*)qname)+1) + sizeof(struct QUESTION)];

	/*
 	*	Start reading answers
 	*/
	stop = 0;

	for(i = 0;i < ntohs(dns->ans_count);i++){
		answers[i].name = readName(pointer,buffer,&stop);
		pointer = pointer + stop;

		answers[i].resource = (struct R_DATA*)(pointer);
		pointer = pointer + sizeof(struct R_DATA);

		if(ntohs(answers[i].resource->type) == 1){
			answers[i].rdata = (unsigned char*)malloc(ntohs(answers[i].resource->data_len));

			for(j = 0;j < ntohs(answers[i].resource->data_len);j++){
				answers[i].rdata[j]=pointer[j];
			}

			answers[i].rdata[ntohs(answers[i].resource->data_len)] = '\0';
			pointer = pointer + ntohs(answers[i].resource->data_len);
		}
		else{
			answers[i].rdata = readName(pointer,buffer,&stop);
			pointer = pointer + stop;
		}
	}

	/*
 	* 	Read the Authority Records
 	*/
	for(i = 0;i < ntohs(dns->auth_count);i++){
		auth[i].name = readName(pointer,buffer,&stop);
		pointer += stop;

		auth[i].resource = (struct R_DATA*)(pointer);
		pointer += sizeof(struct R_DATA);
		
		if(ntohs(auth[i].resource->type) == 1){
			auth[i].rdata = (unsigned char*)malloc(ntohs(auth[i].resource->data_len));
	
			for(j = 0;j < ntohs(auth[i].resource->data_len);j++){
				auth[i].rdata[j]=pointer[j];
			}

			auth[i].rdata[ntohs(auth[i].resource->data_len)]='\0';
			pointer+=ntohs(auth[i].resource->data_len);
		}		
		else{
			auth[i].rdata=readName(pointer,buffer,&stop);
			pointer += stop;
		}
	}

	/*
 	* 	Read the Additional RRs 	
 	*/
	for(i = 0;i < ntohs(dns->add_count);i++){
		addit[i].name = readName(pointer,buffer,&stop);
		pointer += stop;

		addit[i].resource = (struct R_DATA*)(pointer);
		pointer += sizeof(struct R_DATA);

		if(ntohs(addit[i].resource->type) == 1){
			addit[i].rdata = (unsigned char*)malloc(ntohs(addit[i].resource->data_len));
			
			for(j = 0;j < ntohs(addit[i].resource->data_len);j++){
				addit[i].rdata[j] = pointer[j];
			}

			addit[i].rdata[ntohs(addit[i].resource->data_len)]='\0';
			pointer += ntohs(addit[i].resource->data_len);
		}
		else{
			addit[i].rdata = readName(pointer,buffer,&stop);
			pointer += stop;
		}
	}

	/*
	*	Print all answer records
	*/
	printf("\nAnswers: %d\n",ntohs(dns->ans_count));
	for(i = 0; i < ntohs(dns->ans_count);i++){

		printf("answer.NAME = %s ",answers[i].name);
		printf("\nanswer.TYPE = %d",ntohs(answers[i].resource->type));
		printf("\nanswer.CLASS = %d",ntohs(answers[i].resource->_class));
		printf("\nanswer.TTL = %lu",ntohs(answers[i].resource->ttl));
		printf("\nanswer.RDLENGTH = %d",ntohs(answers[i].resource->data_len));
		
		if(ntohs(answers[i].resource->type) == T_A){ 
			long *p;
			p = (long*)answers[i].rdata;
			a.sin_addr.s_addr = (*p);
			printf("\nanswer.RDATA = %s",inet_ntoa(a.sin_addr));
		}
	
		if(ntohs(answers[i].resource->type) == 5){
			printf("\nAlias name = %s\n",answers[i].rdata);
		}

		printf("\n");
	}
	printf("-----------------------------------------------------");

	/*
 	*	Print Authoritive Records
 	*/
	printf("\nAuthority: %d\n",ntohs(dns->auth_count));
	for(i = 0; i < ntohs(dns->auth_count);i++){
		printf("authority.NAME = %s ",auth[i].name);
		printf("\nauthority.TYPE = %d",ntohs(auth[i].resource->type));
		printf("\nauthority.CLASS = %d",ntohs(auth[i].resource->_class));
		printf("\nauthority.TTL = %lu",ntohs(auth[i].resource->ttl));
		printf("\nauthority.RDLENGTH = %d",ntohs(auth[i].resource->data_len));
		
		if(ntohs(auth[i].resource->type) == 2){
			long *p;
			p = (long*)auth[i].rdata;
			a.sin_addr.s_addr = (*p);
			printf("\nauthority.RDATA = %s",inet_ntoa(a.sin_addr));
		}
		printf("\n");
	}
	printf("------------------------------------------------------");

	/*
  	*	Print Additional Records
 	*/
	printf("\nAdditional: %d\n",ntohs(dns->add_count));
	for(i = 0; i < ntohs(dns->add_count);i++){
		printf("additional.NAME = %s ",addit[i].name);
		printf("\nadditional.TYPE = %d",ntohs(addit[i].resource->type));
		printf("\nadditional.CLASS = %d",ntohs(addit[i].resource->_class));
		printf("\nadditional.TTL = %u",ntohs(addit[i].resource->ttl));
		printf("\nadditional.RDLENGTH = %d",ntohs(addit[i].resource->data_len));

		if(ntohs(addit[i].resource->type) == 1){
			long *p;
			p = (long*)addit[i].rdata;
			a.sin_addr.s_addr = (*p);
			printf("\nadditional.RDATA = %s",inet_ntoa(a.sin_addr));
		}
		printf("\n");
	}
	printf("-----------------------------------------------------\n");

	return;
}

/*
 * 
 * */
unsigned char* readName(unsigned char* pointer,unsigned char* buffer,int* count)
{
	unsigned char *name;
	unsigned int p = 0,jumped = 0,offset;
	int i, j;

	*count = 1;
	name = (unsigned char*)malloc(256);

	name[0] = '\0';

	//	Read names in 3ww6google3com0 format
	while(*pointer != 0){
		if(*pointer >= 192){
			offset = (*pointer)*256 + *(pointer+1) - 49152;
			pointer = buffer + offset - 1;
			jumped = 1; 	//Jumped location
		}
		else{
			name[p++] = *pointer;
		}

		pointer = pointer+1;

		if(jumped == 0){
			*count = *count + 1; 	//Count up since havent jumped
		}
	}

	name[p] = '\0';
	if(jumped == 1){
		*count = *count + 1; 	//Number of steps moved forward
	}

	//	Converts 3www6google3com0 into www.google.com
	for(i = 0;i < (int)strlen((const char*)name);i++){
		p = name[i];
		if((int)p > 97){
			if((int)p < 122){
				name[i] = '.';
			}
		}
			
	
		for(j = 0;j < (int)p;j++){
			name[i] = name[i+1];
			i = i+1;
		}
		name[i] = '.';
		
	}
	name[i-1] = '\0';
	return name;
}

/*
 * 	Converts DNS name into the following format: www.google.com --> 3www6google3com 
 */
void formatDNSname(unsigned char* dns,unsigned char* hostname) 
{
	int lock = 0 , i;
	strcat((char*)hostname, ".");

	for(i = 0 ; i < strlen((char*)hostname);i++){
		if(hostname[i] == '.'){
			*dns++ = i-lock;
			for(;lock < i;lock++){
				*dns++=hostname[lock];
			}
			lock++;
		}
	}
	*dns++='\0';
}
