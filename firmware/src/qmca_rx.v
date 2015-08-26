`timescale 1ps / 1ps

/**
 * Project: qmca
 * Author: Philipp Steingrebe <pstg@uni-bonn.de> <philipp@steingrebe.de>
 *
 * Copyright (c) All rights reserved
 * SiLab, Institute of Physics, University of Bonn
 */
 
module qmca_rx
#(
	parameter BASEADDR  = 0,
	parameter HIGHADDR  = 0,
	parameter ABUSWIDTH = 16,
	parameter DBUSWIDTH = 8
)(
   input         bus_clk,
	input         bus_rst,

   // ADC
	input         adc_clk,
   input  [13:0] adc_in0,
   input  [13:0] adc_in1,
   input  [13:0] adc_in2,
   input  [13:0] adc_in3,

   // USB Bus
	input      [15:0] bus_add,
   inout       [7:0] bus_data,
   input             bus_wr,
   input             bus_rd,
	
	input  wire       usb_rd,
	output wire [7:0] usb_data,

	// Debug
	output wire [3:0] state,
	output wire comp
); 

	/**
	 * Wires
	 */
	 
	// Config
	wire  [2:0] conf_channel;
	wire [13:0] conf_threshold;
	wire  [7:0] conf_buf_size;
	wire [11:0] conf_evt_size;
	wire        conf_rst;
	
	// ADC
	wire [13:0] adc_in [3:0];
	assign adc_in[0] = adc_in0;
	assign adc_in[1] = adc_in1;
	assign adc_in[2] = adc_in2;
	assign adc_in[3] = adc_in3;
	
	// FIFO buffer
	wire  [9:0] buf_cnt;
	wire [63:0] buf_din;
	wire [63:0] buf_dout;
	wire        buf_rd;
	wire        buf_wr;
	wire        buf_full;
	
	// FIFO event
	wire [14:0] evt_cnt_rd;
	wire [11:0] evt_cnt_wr;
	wire [63:0] evt_din;
	wire  [7:0] evt_dout;
	wire        evt_wr;
	wire        evt_rd;
	wire        evt_empty;
	wire        evt_full;

	// Channel select
	wire  [1:0] sel_channel;
	wire [13:0] sel_adc_in;

	
	// state mashine
	wire [1:0] sm_channel;
	wire       sm_data;
	wire       sm_collect;
	wire       sm_buf_full;
	wire       sm_evt_full;

	
	/**
	 * Config
	 */

	qmca_conf #(
		.BASEADDR(BASEADDR),
		.HIGHADDR(HIGHADDR)
	) conf (
		.clk(bus_clk),       // (input)
		.rst(bus_rst),       // (input)

		.bus_add(bus_add),   // (input)
		.bus_data(bus_data), // (inout)
		.bus_wr(bus_wr),     // (input)
		.bus_rd(bus_rd),     // (input)
	
		.sm_channel(sm_channel), // (input) [1:0]
		.sm_data(sm_data),       // (input)
		
		.conf_channel(conf_channel),     // (output)
		.conf_threshold(conf_threshold), // (output)
		.conf_buf_size(conf_buf_size),   // (output)
		.conf_evt_size(conf_evt_size),   // (output)
		
		.conf_rst(conf_rst)              // (output)
	);


	/**
	 * Channel select
	 */

	qmca_select select_inst (
		.conf_channel(conf_channel), // (input)

		.adc_in0(adc_in0),           // (input) 
		.adc_in1(adc_in1),           // (input)
		.adc_in2(adc_in2),           // (input)
		.adc_in3(adc_in3),           // (input)
		
		.sel_channel(sel_channel),   // (output) Current maximal channel [3:0]  
		.sel_adc_in(sel_adc_in)      // (output) Current maximal value [13:0]
	);


	/**
	 * comperator
	 */

	qmca_comp comp_inst (
		.clk(adc_clk), .rst(bus_rst),

		.sel_adc_in(sel_adc_in),         // (input)
		.conf_threshold(conf_threshold), // (input)

		.comp(comp)                      // (output)
	);


	/**
	 * state machine 
	 */
	
	assign sm_buf_full = buf_full | buf_cnt    == (conf_buf_size - 1);
	assign sm_evt_full = evt_full | evt_cnt_wr == (conf_evt_size - 2);

	qmca_sm sm_inst (
		.clk(adc_clk),             // (input) Bus clock
		.rst(bus_rst | conf_rst),  // (input) Bus reset
	
		.sel_channel(sel_channel), // (input)
      
		// Requirements
		.comp(comp),               // (input)
		.buf_full(sm_buf_full),    // (input)
		.evt_full(sm_evt_full),    // (input)
		.evt_empty(evt_empty),     // (input)
		
		// Grants
		.sm_collect(sm_collect),   // (output)
		.sm_data(sm_data),         // (output)
		.sm_channel(sm_channel),   // (output)
   
		.state(state)              // (output) [3:0] Current state
	);


	/**
	 * FIFO buffer
	 */
	//reg [63:0] buf_tmp;
	//always @(posedge bus_clk)
	//	if(bus_rst)
	//		buf_tmp <= 64'hAA11BB22CC33DD44;
	
	
	//assign buf_din = buf_tmp;
	assign buf_din = {2'b0, adc_in[0], 2'b0, adc_in[1], 2'b0, adc_in[2], 2'b0, adc_in[3]};

	assign buf_wr  = 1'b1;
	assign buf_rd  = sm_buf_full;

	qmca_fifo_sync fifo_buffer_inst (
		.clk(adc_clk),            // (input)         Clock (ADC-Domain)
		.rst(bus_rst | conf_rst), // (input)         Reset
		
		.wr_en(buf_wr),         // (input)         Write enabled			
		.din(buf_din),          // (input)  [63:0] Data in
		.rd_en(buf_rd),         // (input)         Read enabled
		.dout(buf_dout),        // (output) [63:0] Data out

		.full(),                // (output)        Full
		.almost_full(buf_full), // (output)        Almost_full
		.empty(),               // (output)        Empty
		.data_count(buf_cnt)    // (output)  [7:0] Count
	);


	/**
	 * FIFO event
	 */
	
	//assign evt_din = buf_dout;
	assign evt_wr  = sm_collect;
	assign evt_rd  = usb_rd; // sm_data &  usb_rd;
	
	assign evt_empty = (evt_cnt_rd == 0);
	
	//assign usb_data = evt_rd ? evt_dout : 8'b0;

	reg [7:0] evt_tmp;
	always @(posedge bus_clk)
		evt_tmp <= evt_dout;
	assign usb_data = evt_tmp;
	
	qmca_fifo_async fifo_event_inst (
		.wr_clk(adc_clk),           // (input)         Write clock (ADC-Domain)
		.rd_clk(bus_clk),           // (input)         Read clock (BUS-Domain)
		.rst(bus_rst | conf_rst),   // (input)         Reset

		.wr_en(evt_wr),             // (input)         Write enabled
		.din(buf_dout),             // (input)  [63:0] Data in
		.rd_en(evt_rd),             // (input)         Read enabled
		.dout(evt_dout),            // (output)  [7:0] Data out

		.full(evt_full),            // (output)        Full
		.empty(),                   // (output)        Empty
		.rd_data_count(evt_cnt_rd), // (output) [14:0] Count (read)
		.wr_data_count(evt_cnt_wr)  // (output) [11:0] Count (write)
	);

endmodule
