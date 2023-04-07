    library ieee;
    use ieee.std_logic_1164.all;
    use ieee.numeric_std.all;
  


    entity SevenSegment is
      port (
          clk : in std_logic;
          sw : in std_logic_vector(15 downto 0);
          led : out std_logic_vector(15 downto 0);
          sseg_ca : out std_logic_vector(6 downto 0);
          sseg_an : out std_logic_vector(7 downto 0)
        );
    end SevenSegment;
  


    architecture arch_SevenSegment of SevenSegment is
      signal buffer_led : std_logic_vector(15 downto 0);
      signal buffer_sseg_ca : std_logic_vector(6 downto 0);
      signal buffer_sseg_an : std_logic_vector(7 downto 0);
    begin
    -- CONCURRENT BLOCK (buffer assignment)
      led <= buffer_led;
      sseg_ca <= buffer_sseg_ca;
      sseg_an <= buffer_sseg_an;
    -- Block ()
        process(clk)
          variable temp : std_logic_vector(6 downto 0);
        begin
          if rising_edge(clk) then
            case sw(3 downto 0) is
              when "0000" =>
                temp := "1000000";
              when "0001" =>
                temp := "1111001";
              when "0010" =>
                temp := "0100100";
              when "0011" =>
                temp := "0110000";
              when "0100" =>
                temp := "0011001";
              when "0101" =>
                temp := "0010010";
              when "0110" =>
                temp := "0000010";
              when "0111" =>
                temp := "1111000";
              when "1000" =>
                temp := "0000000";
              when "1001" =>
                temp := "0010000";
              when "1010" =>
                temp := "0001000";
              when "1011" =>
                temp := "0000011";
              when "1100" =>
                temp := "1000110";
              when "1101" =>
                temp := "0100001";
              when "1110" =>
                temp := "0000110";
              when "1111" =>
                temp := "0001110";
              when others =>
                null;
            end case;
            buffer_sseg_ca <= temp;
          end if;
        end process;
      

    end;
