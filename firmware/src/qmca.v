/**
 * Project: qMCA
 * Author: Michael Daas
 *
 * Copyright (c) All rights reserved
 * SiLab, Institute of Physics, University of Bonn
 */

`timescale 1ns / 1ps

module qmca (
    // Base clock 48 MHz
    input wire fclk_in, 

    // USB full speed 
    inout wire  [7:0] usb_data,
    input wire [15:0] usb_add,
    input wire        usb_rd,
    input wire        usb_wr,
     
    inout wire [7:0] FD,
    input wire FREAD,
    input wire FSTROBE,
    input wire FMODE,

    output wire [19:0] SRAM_A,
    inout wire [15:0] SRAM_IO,
    output wire SRAM_BHE_B,
    output wire SRAM_BLE_B,
    output wire SRAM_CE1_B,
    output wire SRAM_OE_B,
    output wire SRAM_WE_B,


    // DEBUG
    output wire        led1,
    output wire        led2,
    output wire        led3,
    output wire        led4,
    output wire        led5,
    output wire  [1:0] lemo_tx,

    // I2C
    inout sda,
    inout scl,

    // FADC Config (SPI) 
    output adc_csn,  // Chip Selection
    output adc_sclk, // Data Clock
    output adc_sdi,  // Slave Data In
    input  adc_sdo,  // Slave Data Out

    // FADC
    output       adc_enc_p, // Encoder Clock
    output       adc_enc_n,
    input        adc_dco_p, // Data Clock
    input        adc_dco_n,
    input        adc_fco_p, // Frame Clock
    input        adc_fco_n,
    input  [3:0] adc_out_p, // Data Bits 1-4
    input  [3:0] adc_out_n
);

    //{{{ Const
    // FADC SPI address space
    localparam SPI_ADC_BASEADDR = 16'h0000;                 // 0x0000
    localparam SPI_ADC_HIGHADDR = SPI_ADC_BASEADDR + 31;    // 0x001f
     
    localparam FIFO_BASEADDR = 16'h0020;                    // 0x0020
    localparam FIFO_HIGHADDR = FIFO_BASEADDR + 15;          // 0x002f

    localparam ADC_RX_CH0_BASEADDR = 16'h0030;                 // 0x0030
    localparam ADC_RX_CH0_HIGHADDR = ADC_RX_CH0_BASEADDR + 15; // 0x003f

    localparam GPIO_TH_BASEADDR = 16'h0100;                 
    localparam GPIO_TH_HIGHADDR = GPIO_TH_BASEADDR + 16'h00ff; 
     
    /**
     * Debug
     * led1: SM State
     * led2: -- " --
     * led3: -- " --
     * led4: -- " --
     * led5: FIFO full | FIFO near full
     */
     wire led[4:0];
     assign led1 = led[0];
     assign led2 = led[1];
     assign led3 = led[2];
     assign led4 = led[3];
     assign led5 = led[4];


    /**
      * I2C Bus
      * Disable I2C by setting sda and scl 
      * to high impedance
      */
    assign sda = 1'bz;
    assign scl = 1'bz;
    
    
     /**
      * Setup System Clocks
      * bus_clk 48 MHz, spi_clk 12 MHz, 
      * adc_enc 10 MHz, adc_clk 160 MHz
      */
    (* KEEP = "{TRUE}" *) // ???
    wire bus_clk; // Clock USB Bus
    (* KEEP = "{TRUE}" *)
    wire spi_clk; // Clock FADC SPI Bus
    (* KEEP = "{TRUE}" *)
    wire adc_enc; // Clock FADC Encoder
    (* KEEP = "{TRUE}" *)
    wire adc_clk; // Clock FADC Readout (16 x clock FADC Encoder)
     
    wire clk_locked; // Clockgen clocks locked 
     
    qmca_clk_gen qmca_clk_gen_inst(
        .CLKIN(fclk_in),     // (Input)
          
        .BUS_CLK(bus_clk),   // (Output) Bus Clock USB
        .SPI_CLK(spi_clk),   // (Output) SPI/BUS Clock
        .ADC_ENC(adc_enc),   // (Output) ADC encoder Clock
        .ADC_CLK(adc_clk),   // (Output) ADC readout Clock
          
        .LOCKED(clk_locked), // (Output) PLL locked
          
          // Unused
        .U2_CLK40(),
        .U2_CLK320()
    );


    /**
      * Setup Bus-Reset
      * Keeps bus_rst triggered for 128 bus clocks
      */

    wire bus_rst;
    reset_gen reset_gen_i(.CLK(bus_clk), .RST(bus_rst));     
    
    // -------  BUS SYGNALING  ------- //
    wire [15:0] bus_add;
    wire bus_rd, bus_wr;
     
    assign bus_add = usb_add - 16'h4000;
    assign bus_rd = ~usb_rd;
    assign bus_wr = ~usb_wr;
    
    
    // -------  USER MODULES  ------- //
     
     wire [1:0] SEL_ADC_CH; 
     wire [13:0] TH;
     gpio #(
         .BASEADDR(GPIO_TH_BASEADDR),
         .HIGHADDR(GPIO_TH_HIGHADDR),
         .IO_WIDTH(16),
         .IO_DIRECTION(16'hffff)
      ) i_gpio_rx (
        .BUS_CLK(bus_clk), 
        .BUS_RST(bus_rst), 
        .BUS_ADD(bus_add),
        .BUS_DATA(usb_data),
        .BUS_RD(bus_rd),
        .BUS_WR(bus_wr),
        .IO({SEL_ADC_CH, TH})
     );


     // Serial Peripheral Interface (SPI) bus to ADC
     
     wire CE_1HZ; // use for sequential logic
     wire CLK_1HZ; // don't connect to clock input, only combinatorial logic
     clock_divider #(
            .DIVISOR(30)
     ) i_clock_divisor_40MHz_to_1Hz (
            .CLK(spi_clk),
            .RESET(1'b0),
            .CE(CE_1HZ),
            .CLOCK(CLK_1HZ)
     );

    wire adc_en;
     spi #( 
        .BASEADDR(SPI_ADC_BASEADDR), 
        .HIGHADDR(SPI_ADC_HIGHADDR), 
        .MEM_BYTES(2) 
    ) spi_fadc (
        .BUS_CLK(bus_clk), // (input) Bus clock
        .BUS_RST(bus_rst), // (input) Bus reset
          
        .BUS_ADD(bus_add),
        .BUS_DATA(usb_data),
        .BUS_RD(bus_rd),
        .BUS_WR(bus_wr),
          
        .SPI_CLK(CLK_1HZ), // (input)  SPI clock
        .SCLK(adc_sclk),   // (output) SPI clock
        .SDI(adc_sdi),     // (output) SPI slave data in
        .SDO(adc_sdo),     // (input)  SPI slave data out
        .SEN(adc_en),      // (output) 
        .SLD()
    );
     
    assign adc_csn = !adc_en;


    /**
     * GPAC FADC I/O buffer (gpac_adc_iobuf)
     * Deserializes the bitstreams of all 4 FADC channels
     */

    wire [13:0] adc_out [3:0];
    wire adc_fco, adc_dco;
    
    gpac_adc_iobuf gpac_adc_iobuf(
        .ADC_CLK(adc_clk),
 
        .ADC_DCO_P(adc_dco_p),  // (input)
        .ADC_DCO_N(adc_dco_n),  // (input)
        .ADC_DCO(adc_dco),      // (output)
    
        .ADC_FCO_P(adc_fco_p),  // (input)
        .ADC_FCO_N(adc_fco_n),  // (input)
        .ADC_FCO(adc_fco),      // (output)

        .ADC_ENC(adc_enc),      // (input)
        .ADC_ENC_P(adc_enc_p),  // (output)
        .ADC_ENC_N(adc_enc_n),  // (output)

        .ADC_IN_P(adc_out_p),   // (input)
        .ADC_IN_N(adc_out_n),   // (input)
        
        .ADC_IN0(adc_out[0]),   // (output)
        .ADC_IN1(adc_out[1]),   // (output)
        .ADC_IN2(adc_out[2]),   // (output)
        .ADC_IN3(adc_out[3])    // (output)
    );


    /**
     * Setup QMCA Readout
     */

    wire [3:0] FIFO_EMPTY_ADC, FIFO_READ;
    wire [31:0] FIFO_DATA_ADC [3:0];

    reg adc_trig;
    always@(posedge adc_enc)
        adc_trig <= adc_out[SEL_ADC_CH] > TH;
     
    wire ADC_TRIG ;
    assign ADC_TRIG = adc_out[SEL_ADC_CH] > TH && adc_trig == 0;

    gpac_adc_rx 
    #(
        .BASEADDR(ADC_RX_CH0_BASEADDR), 
        .HIGHADDR(ADC_RX_CH0_HIGHADDR),
        .ADC_ID(0), 
        .HEADER_ID(0) 
    ) i_gpac_adc_rx
    (
        .ADC_ENC(adc_enc),
        .ADC_IN(adc_out[SEL_ADC_CH]),
        .ADC_SYNC(1'b0),
        .ADC_TRIGGER(ADC_TRIG),

        .BUS_CLK(bus_clk),
        .BUS_RST(bus_rst),
        .BUS_ADD(bus_add),
        .BUS_DATA(usb_data),
        .BUS_RD(bus_rd),
        .BUS_WR(bus_wr), 

        .FIFO_READ(FIFO_READ[0]),
        .FIFO_EMPTY(FIFO_EMPTY_ADC[0]),
        .FIFO_DATA(FIFO_DATA_ADC[0]),

        .LOST_ERROR()
    ); 

    assign FIFO_EMPTY_ADC[3:1] = 3'b111;
    
    wire ARB_READY_OUT, ARB_WRITE_OUT;
    wire [31:0] ARB_DATA_OUT;

    rrp_arbiter 
    #( 
        .WIDTH(4)
    ) i_rrp_arbiter
    (
        .RST(bus_rst),
        .CLK(bus_clk),
        .WRITE_REQ(~FIFO_EMPTY_ADC),
        .HOLD_REQ(4'b0),
        .DATA_IN({FIFO_DATA_ADC[3],FIFO_DATA_ADC[2],FIFO_DATA_ADC[1],FIFO_DATA_ADC[0]}),
        .READ_GRANT(FIFO_READ),
        .READY_OUT(ARB_READY_OUT),
        .WRITE_OUT(ARB_WRITE_OUT),
        .DATA_OUT(ARB_DATA_OUT)
    );

    wire USB_READ;
    assign USB_READ = FREAD && FSTROBE;

    sram_fifo 
    #(
        .BASEADDR(FIFO_BASEADDR), 
        .HIGHADDR(FIFO_HIGHADDR)
    ) i_out_fifo (

        .BUS_CLK(bus_clk),
        .BUS_RST(bus_rst),
        .BUS_ADD(bus_add),
        .BUS_DATA(usb_data),
        .BUS_RD(bus_rd),
        .BUS_WR(bus_wr), 
          
        .SRAM_A(SRAM_A),
        .SRAM_IO(SRAM_IO),
        .SRAM_BHE_B(SRAM_BHE_B),
        .SRAM_BLE_B(SRAM_BLE_B),
        .SRAM_CE1_B(SRAM_CE1_B),
        .SRAM_OE_B(SRAM_OE_B),
        .SRAM_WE_B(SRAM_WE_B),
        .USB_READ(USB_READ),
        .USB_DATA(FD),

        .FIFO_READ_NEXT_OUT(ARB_READY_OUT),
        .FIFO_EMPTY_IN(!ARB_WRITE_OUT),
        .FIFO_DATA(ARB_DATA_OUT),
        .FIFO_NOT_EMPTY(),
        .FIFO_READ_ERROR(),
        .FIFO_FULL(),
        .FIFO_NEAR_FULL()    

    );

    assign lemo_tx = 0;
    
endmodule
