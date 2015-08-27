/**
 * ------------------------------------------------------------
 * Copyright (c) All rights reserved 
 * SiLab, Institute of Physics, University of Bonn
 * ------------------------------------------------------------
 */
 
`timescale 1ns / 1ps
`default_nettype none

module qmca_clk_gen(
    input CLKIN, // 48M
	 
    output BUS_CLK, // BUS_CLK is 48M							output from 1. DCM
    output SPI_CLK, // SPI_CLK is 12 MHz (48M / 4 = 12M)			output from 1. DCM
	 
    output ADC_ENC, // ADC_ENC is 10 MHz ( 80M / 8 = 10 M)		output from 2. DCM
    output ADC_CLK, // ADC_CLK is 160 MHz ( 80M * 2 = 160 M)  	output from 1. DCM

    output U2_CLK40,  // TDC			40M currently					output from 2. DCM
    output U2_CLK320, // TDC			320M currently					output from 2. DCM
	 
    output LOCKED
    );

    wire CLK2_FX_BUF;
    wire GND_BIT;
    assign GND_BIT = 0;
    wire CLKD10MHZ;
    wire CLKFX_BUF, CLKOUTFX, CLKDV, CLKDV_BUF;

    wire CLK0_BUF; // Buffered input of DCM1

    wire CLKFX_160FB; // Feedback to DCM2 (buffered input of DCM2)

    wire CLKOUT160, CLKDV_10;
    wire CLK2_0, CLK2_FX;
    wire CLKFX_40;

    wire CLK2X_320M;
    wire CLK2X_320M_BUF;
	 
    wire CLKFX_160;

    wire U2_LOCKED_INV_RST;
    wire U2_FDS_Q_OUT;
    wire U2_FD1_Q_OUT;
    wire U2_FD2_Q_OUT;
    wire U2_FD3_Q_OUT;
    wire U2_OR3_O_OUT;
    wire U2_RST_IN;


    assign ADC_ENC = CLKD10MHZ;
    assign ADC_CLK = CLKOUT160;

	 assign U2_CLK40 = CLK2_FX_BUF;
	 assign U2_CLK320 = CLK2X_320M_BUF;

    BUFG CLKFX_BUFG_INST (.I(CLKFX_BUF), .O(CLKOUTFX)); 
    
	 BUFG CLKFB_BUFG_INST (.I(CLK0_BUF), .O(BUS_CLK));
	 
    BUFG CLKDV_BUFG_INST (.I(CLKDV), .O(CLKDV_BUF));

    assign SPI_CLK = CLKDV_BUF;


   
	// First DCM gets 48 MHz clock
	// --> Makes 160 MHz output on CLKFX (48 * 10/3) for next DCM as input and for ADC_CLK
	// --> Makes 12 MHz output on CLKDV (48 / 4) for SPI_CLK
   DCM #(
         .CLKDV_DIVIDE(16), // Divide by: 1.5,2.0,2.5,3.0,3.5,4.0,4.5,5.0,5.5,6.0,6.5
         // 7.0,7.5,8.0,9.0,10.0,11.0,12.0,13.0,14.0,15.0 or 16.0
         .CLKFX_DIVIDE(3), // Can be any Integer from 1 to 32
         .CLKFX_MULTIPLY(10), // Can be any Integer from 2 to 32
         .CLKIN_DIVIDE_BY_2("FALSE"), // TRUE/FALSE to enable CLKIN divide by two feature
         .CLKIN_PERIOD(20.833), // Specify period of input clock
         .CLKOUT_PHASE_SHIFT("NONE"), // Specify phase shift of NONE, FIXED or VARIABLE
         .CLK_FEEDBACK("1X"), // Specify clock feedback of NONE, 1X or 2X
         .DESKEW_ADJUST("SYSTEM_SYNCHRONOUS"), // SOURCE_SYNCHRONOUS, SYSTEM_SYNCHRONOUS or
         // an Integer from 0 to 15
         .DFS_FREQUENCY_MODE("LOW"), // HIGH or LOW frequency mode for frequency synthesis
         .DLL_FREQUENCY_MODE("LOW"), // HIGH or LOW frequency mode for DLL
         .DUTY_CYCLE_CORRECTION("TRUE"), // Duty cycle correction, TRUE or FALSE
         .FACTORY_JF(16'h8080), // FACTORY JF values
         .PHASE_SHIFT(0), // Amount of fixed phase shift from -255 to 255
         .STARTUP_WAIT("TRUE") // Delay configuration DONE until DCM_SP LOCK, TRUE/FALSE
         ) DCM_BUS (
         .CLKFB(BUS_CLK), 
         .CLKIN(CLKIN), 
         .DSSEN(GND_BIT), 
         .PSCLK(GND_BIT), 
         .PSEN(GND_BIT), 
         .PSINCDEC(GND_BIT), 
         .RST(GND_BIT),
         .CLKDV(CLKDV),
         .CLKFX(CLKFX_160), 
         .CLKFX180(), 
         .CLK0(CLK0_BUF), 
         .CLK2X(), 
         .CLK2X180(), 
         .CLK90(), 
         .CLK180(), 
         .CLK270(), 
         .LOCKED(LOCKED), 
         .PSDONE(), 
         .STATUS());

	// buffer 160 M output from DCM1 and use buffered 160 M as input to DCM2
   BUFG CLKFX_2_BUFG_INST (.I(CLKFX_160), .O(CLKOUT160));
	
   BUFG CLKDV_2_BUFG_INST (.I(CLKDV_10), .O(CLKD10MHZ));
	
	// buffer input to DCM2 (160 MHz) and use as feedback for DCM2
   BUFG CLKFB_2_BUFG_INST (.I(CLK2_0), .O(CLKFX_160FB));
   
	BUFG CLKFX2_2_BUFG_INST (.I(CLK2_FX), .O(CLK2_FX_BUF));


	BUFG CLK2X_320_BUFG_INST (.I(CLK2X_320M), .O(CLK2X_320M_BUF));

	// Second DCM gets 160 MHz clock
	// --> Makes 320 MHz output on CLK2X for TDC_320_CLK
	// --> Makes 40 MHz output on CLKFX (1 / 4) for TDC_40_CLK
	// --> Makes 10 MHz output on CLKDV (1 / 16) for ADC_ENC
   DCM #(
         .CLKDV_DIVIDE(16.0), // Divide by: 1.5,2.0,2.5,3.0,3.5,4.0,4.5,5.0,5.5,6.0,6.5
         // 7.0,7.5,8.0,9.0,10.0,11.0,12.0,13.0,14.0,15.0 or 16.0
         .CLKFX_DIVIDE(8), // Can be any Integer from 1 to 32
         .CLKFX_MULTIPLY(2), // Can be any Integer from 2 to 32
         .CLKIN_DIVIDE_BY_2("FALSE"), // TRUE/FALSE to enable CLKIN divide by two feature
         .CLKIN_PERIOD(25.0), // Specify period of input clock
         .CLKOUT_PHASE_SHIFT("NONE"), // Specify phase shift of NONE, FIXED or VARIABLE
         .CLK_FEEDBACK("1X"), // Specify clock feedback of NONE, 1X or 2X
         .DESKEW_ADJUST("SYSTEM_SYNCHRONOUS"), // SOURCE_SYNCHRONOUS, SYSTEM_SYNCHRONOUS or
         // an Integer from 0 to 15
         .DFS_FREQUENCY_MODE("LOW"), // HIGH or LOW frequency mode for frequency synthesis
         .DLL_FREQUENCY_MODE("LOW"), // HIGH or LOW frequency mode for DLL
         .DUTY_CYCLE_CORRECTION("TRUE"), // Duty cycle correction, TRUE or FALSE
         .FACTORY_JF(16'h8080), // FACTORY JF values
         .PHASE_SHIFT(0), // Amount of fixed phase shift from -255 to 255
         .STARTUP_WAIT("TRUE") // Delay configuration DONE until DCM_SP LOCK, TRUE/FALSE
     ) DCM_CMD (
         .DSSEN(GND_BIT), 
         .CLK0(CLK2_0), // 0 degree DCM_SP CLK output
         .CLK180(), // 180 degree DCM_SP CLK output
         .CLK270(), // 270 degree DCM_SP CLK output
         .CLK2X(CLK2X_320M), // 2X DCM_SP CLK output    -------------------------------320 M TDC_320_CLK
         .CLK2X180(), // 2X, 180 degree DCM_SP CLK out
         .CLK90(), // 90 degree DCM_SP CLK output
         .CLKDV(CLKDV_10), // Divided DCM_SP CLK out (CLKDV_DIVIDE) -------------------------------10 M ADC_ENC
         .CLKFX(CLK2_FX), // DCM_SP CLK synthesis out (M/D) -------------------------------40 M TDC_40_CLK
         .CLKFX180(), // 180 degree CLK synthesis out
         .LOCKED(), // DCM_SP LOCK status output
         .PSDONE(), // Dynamic phase adjust done output
         .STATUS(), // 8-bit DCM_SP status bits output
         .CLKFB(CLKFX_160FB), // DCM_SP clock feedback
         .CLKIN(CLKOUT160), // Clock input (from IBUFG, BUFG or DCM_SP)
         .PSCLK(GND_BIT), // Dynamic phase adjust clock input
         .PSEN(GND_BIT), // Dynamic phase adjust enable input
         .PSINCDEC(GND_BIT), // Dynamic phase adjust increment/decrement
         .RST(U2_RST_IN)// // DCM_SP asynchronous reset input
     );
	  
	  INV  U1_INV_INST (.I(LOCKED), 
					  .O(U2_LOCKED_INV_RST));

		FDS  U2_FDS_INST (.C(BUS_CLK), 
							  .D(GND_BIT), 
							  .S(GND_BIT), 
							  .Q(U2_FDS_Q_OUT));
		FD  U2_FD1_INST (.C(BUS_CLK), 
							 .D(U2_FDS_Q_OUT), 
							 .Q(U2_FD1_Q_OUT));
		FD  U2_FD2_INST (.C(BUS_CLK), 
							 .D(U2_FD1_Q_OUT), 
							 .Q(U2_FD2_Q_OUT));
		FD  U2_FD3_INST (.C(BUS_CLK), 
							 .D(U2_FD2_Q_OUT), 
							 .Q(U2_FD3_Q_OUT));
		OR2  U2_OR2_INST (.I0(U2_LOCKED_INV_RST), 
							  .I1(U2_OR3_O_OUT), 
							  .O(U2_RST_IN));
		OR3  U2_OR3_INST (.I0(U2_FD3_Q_OUT), 
							  .I1(U2_FD2_Q_OUT), 
							  .I2(U2_FD1_Q_OUT), 
							  .O(U2_OR3_O_OUT));
	  
	  
     
endmodule
