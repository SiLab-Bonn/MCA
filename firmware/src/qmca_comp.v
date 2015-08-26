`timescale 1ps / 1ps

/**
 * Project: qmca
 * Module: Comperator
 * Author: Philipp Steingrebe <pstg@uni-bonn.de> <philipp@steingrebe.de>
 *
 * Copyright (c) All rights reserved
 * SiLab, Institute of Physics, University of Bonn
 */

module qmca_comp
#(
	parameter OFFSET = 4'hF
)(
	input         clk, rst,
	
	input  [13:0] sel_adc_in,
	input  [15:0] conf_threshold,

	output        comp
);
	reg        tmp_comp;
	reg        tmp_comp_del;
	
	reg [15:0] tmp_threshold;
	
	assign comp = tmp_comp & !tmp_comp_del;
	
	always @* begin
		case(tmp_comp)
			1'b1: tmp_threshold = conf_threshold - OFFSET;
			1'b0: tmp_threshold = conf_threshold;
			default: tmp_threshold = conf_threshold;
		endcase
	end
	
	always @ (posedge clk) begin
		if (rst == 1'b1) begin
			tmp_comp     <= 1'b0;
			tmp_comp_del <= 1'b0;
		end

		else begin
			if (sel_adc_in > tmp_threshold)
				tmp_comp <= 1'b1;
			else
				tmp_comp <= 1'b0;
		end
		
		tmp_comp_del <= tmp_comp;
	end	 
endmodule
