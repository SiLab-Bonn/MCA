`timescale 1ns / 1ps

module qmca_sm(
	input        clk, rst,
	input  [1:0] sel_channel,
	
	// Requirements
	input comp, evt_full, evt_empty, buf_full,

	// Grants
	output reg         sm_data,
	output reg         sm_collect,
	output reg   [1:0] sm_channel,

	// Debug
	output wire  [3:0] state
);

	// states
	parameter ST_BUFFER  = 4'b0001;
	parameter ST_IDLE    = 4'b0010;
	parameter ST_EVENT   = 4'b0100;
	parameter ST_READOUT = 4'b1000;

	reg [3:0] state_current;
	reg [3:0] state_next;
	assign state = state_current;
	
	// Log sel_channel while idle
	always @(negedge clk) begin
		if (rst == 1)
			sm_channel <= 2'b00;
		else if (state == ST_IDLE)
			sm_channel <= sel_channel;
	end

	// SM driver
	always @(posedge clk) begin
		if (rst == 1)
			state_current <= ST_BUFFER;
		else
			state_current <= state_next;
	end
			
	always @(state_current or comp or buf_full or evt_full or evt_empty) begin
				
		case (state_current)
			// state BUFFER
			// Buffer current signal
			ST_BUFFER: begin
				sm_collect = 0;
				sm_data    = 0;
				
				if (buf_full == 1)
					state_next = ST_IDLE;
				else
					state_next = ST_BUFFER;
			end
			
			// state IDLE
			// Wait for next event
			ST_IDLE: begin
				sm_collect = 0;
				sm_data    = 0;

				if (comp == 1) begin
					state_next = ST_EVENT;
				end
				else begin
					state_next = ST_IDLE;
				end
			end
				
			// state EVENT
			// Collect event data until event-fifo is full
			ST_EVENT: begin
				sm_collect = 1'b1;
				sm_data    = 1'b0;
				
				if (evt_full == 1)
					state_next = ST_READOUT;
				else
					state_next = ST_EVENT;
			end
			
			// state READOUT
			// Transfer the event-fifo content and switch to idle-state
			ST_READOUT: begin
				sm_collect = 0;
				sm_data    = 1;
				
				if (evt_empty == 1)
					state_next = ST_IDLE;
				else
					state_next = ST_READOUT;
			end
				
			default:	begin
				sm_collect = 0;
				sm_data    = 0;
				state_next = ST_BUFFER;
			end
		endcase
	end	
endmodule
