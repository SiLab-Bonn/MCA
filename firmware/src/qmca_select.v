`timescale 1ps / 1ps

/**
 * Project: qmca
 * Author: Philipp Steingrebe <pstg@uni-bonn.de> <philipp@steingrebe.de>
 *
 * Copyright (c) All rights reserved
 * SiLab, Institute of Physics, University of Bonn
 */

module qmca_select(
	input  [2:0] conf_channel,
	input [13:0] adc_in0,
	input [13:0] adc_in1,
	input [13:0] adc_in2,
	input [13:0] adc_in3,
	
	output reg  [1:0] sel_channel,
	output reg [13:0] sel_adc_in
);

	always @(conf_channel or adc_in0 or adc_in1 or adc_in2 or adc_in3) begin
		case(conf_channel)
			// Channel #1
			3'b000: begin
				sel_channel = 2'b00;
				sel_adc_in = adc_in0;
			end
			// Channel #2
			3'b001: begin
				sel_channel = 2'b01;
				sel_adc_in = adc_in1;
			end
			// Channel #3
			3'b010: begin
				sel_channel = 2'b10;
				sel_adc_in = adc_in2;
			end
			// Channel #4
			3'b011: begin
				sel_channel = 2'b11;
				sel_adc_in = adc_in3;
			end
			// Auto channel
			default: begin
				if (adc_in0 >= adc_in1 && adc_in0 >= adc_in2 && adc_in0 >= adc_in3) begin
					sel_channel = 2'b00;
					sel_adc_in = adc_in0;
				end
				else if(adc_in1 >= adc_in2 && adc_in1 >= adc_in3) begin
					sel_channel = 2'b01;
					sel_adc_in = adc_in1;
				end
				else if(adc_in2 >= adc_in3) begin
					sel_channel = 2'b10;
					sel_adc_in = adc_in2;
				end
				else begin
					sel_channel = 2'b11;
					sel_adc_in = adc_in3;
				end
			end
		endcase
	end
endmodule
