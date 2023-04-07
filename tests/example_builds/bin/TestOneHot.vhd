    library ieee;
    use ieee.std_logic_1164.all;
    use ieee.numeric_std.all;
  


    entity TestOneHot is
      port (
          clk : in std_logic;
          sw : in std_logic_vector(15 downto 0);
          led : out std_logic_vector(15 downto 0);
          sseg_ca : out std_logic_vector(6 downto 0);
          sseg_an : out std_logic_vector(7 downto 0)
        );
    end TestOneHot;
  


    architecture arch_TestOneHot of TestOneHot is
      signal buffer_led : std_logic_vector(15 downto 0);
      signal buffer_sseg_ca : std_logic_vector(6 downto 0);
      signal buffer_sseg_an : std_logic_vector(7 downto 0);
      signal temp : std_logic;
    begin
    -- CONCURRENT BLOCK (buffer assignment)
      led <= buffer_led;
      sseg_ca <= buffer_sseg_ca;
      sseg_an <= buffer_sseg_an;
    -- Block ()
      -- CONCURRENT BLOCK ()
        temp <= '1' when sw /= "0000000000000000" else '0';
        clk <= temp;
      

    end;
