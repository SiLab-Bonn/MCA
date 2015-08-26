`timescale 1ns / 1ps

/**
 * Project: qmca
 * Author: Philipp Steingrebe <pstg@uni-bonn.de> <philipp@steingrebe.de>
 *
 * Copyright (c) All rights reserved
 * SiLab, Institute of Physics, University of Bonn
 */

module qmca_conf
#(
	parameter BASEADDR  = 0,
	parameter HIGHADDR  = 0,
	parameter ABUSWIDTH = 16,
	parameter DBUSWIDTH = 8,
	
	parameter DEF_THRESHOLD = 16'h3FFF,
	parameter DEF_BUF_SIZE  =  8'h7F,
	parameter DEF_EVT_SIZE  = 16'h03FF,
	parameter DEF_CHANNEL   =  8'b0000_0100
)(
	input clk, rst, bus_rd, bus_wr,

	input [ABUSWIDTH-1:0] bus_add,
	inout [DBUSWIDTH-1:0] bus_data,
	
	input [1:0]           sm_channel,
	input                 sm_data,

	output wire conf_rst,
	
	output wire [13:0] conf_threshold,
	output wire  [7:0] conf_buf_size,
	output wire [11:0] conf_evt_size,
	output wire  [2:0] conf_channel
);

	reg [15:0] tmp_threshold; // Signal threshold
	reg  [7:0] tmp_channel;   // Channel select(3'b000 #1 | 3'b001 #2 | 3'b010 #3 | 3'b011 #4 | 3'b100 #All)
	reg  [7:0] tmp_buf_size;  // Buffer FIFO size (max. 256)
	reg [15:0] tmp_evt_size;  // Event FIFO size (max. 4095)
	
	reg [DBUSWIDTH-1:0] tmp_data;
	
	assign conf_threshold = tmp_threshold[13:0];
	assign conf_channel   = tmp_channel[2:0];
	assign conf_buf_size  = tmp_buf_size[7:0];
	assign conf_evt_size  = tmp_evt_size[11:0];



	// Check whether valid addresse is valid.
	wire valid;
	assign valid = (bus_add >= BASEADDR && bus_add <= HIGHADDR);
	
	// Decode address
	wire [15:0] tmp_add;
	assign tmp_add = valid ? bus_add - BASEADDR : 'b0; //{ABUSWIDTH{1'b0}};
	
	// Streched reset 
	reg [2:0] rst_cnt;
	assign conf_rst = ~rst_cnt[2];
	
	always @(posedge clk)
		if (rst || valid & bus_wr)
			rst_cnt <= 'b0;
		else if(~rst_cnt[2])
			rst_cnt <= rst_cnt + 1;
	
	// Connect bus_data (inout) to temp storage
	assign bus_data = (valid && bus_wr) ? {DBUSWIDTH{1'bz}} : (valid ? tmp_data : {DBUSWIDTH{1'bz}});

	always @(posedge clk) begin
		// Reset
		if(rst || (tmp_add == 0 && bus_wr)) begin
			tmp_threshold <= DEF_THRESHOLD;
			tmp_channel   <= DEF_CHANNEL;
			tmp_buf_size  <= DEF_BUF_SIZE;
			tmp_evt_size  <= DEF_EVT_SIZE;
		end
	 
		// Read
		else if (bus_rd & valid)
			case(tmp_add)
				// 0 is reserved for soft-reset
				1: tmp_data <= {5'b0, sm_data, sm_channel}; // (readonly)

				2:	tmp_data <= tmp_channel;
				3:	tmp_data <= tmp_threshold[7:0];
				4:	tmp_data <= tmp_threshold[15:8];
				5: tmp_data <= tmp_buf_size[7:0];
				6: tmp_data <= tmp_evt_size[7:0];
				7: tmp_data <= tmp_evt_size[15:8];
				default:
					tmp_data <= 8'h00;
			endcase

		// Write
		else if(bus_wr & valid)
			case (tmp_add)
				// 0 is reserved for soft-reset
				// 1 is readonly
				
				2: tmp_channel         <= bus_data;
				3: tmp_threshold[7:0]  <= bus_data;
				4: tmp_threshold[15:8] <= bus_data;
				5: tmp_buf_size[7:0]   <= bus_data;
				6: tmp_evt_size[7:0]   <= bus_data; 
				7: tmp_evt_size[15:8]  <= bus_data;
			endcase
	end
endmodule
