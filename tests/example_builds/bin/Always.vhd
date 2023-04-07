    library ieee;
    use ieee.std_logic_1164.all;
    use ieee.numeric_std.all;
  


    entity Always is
      port (
          clk : in std_logic;
          sw : in std_logic_vector(15 downto 0);
          led : out std_logic_vector(15 downto 0);
          sseg_ca : out std_logic_vector(6 downto 0);
          sseg_an : out std_logic_vector(7 downto 0)
        );
    end Always;
  


    architecture arch_Always of Always is
      signal buffer_led : std_logic_vector(15 downto 0);
      signal buffer_sseg_ca : std_logic_vector(6 downto 0);
      signal buffer_sseg_an : std_logic_vector(7 downto 0);
      constant const : integer := 1;
      signal sig : unsigned(15 downto 0) := "0000000000000001";
    begin
    -- CONCURRENT BLOCK (buffer assignment)
      led <= buffer_led;
      sseg_ca <= buffer_sseg_ca;
      sseg_an <= buffer_sseg_an;
    -- Block ()
      -- Block ()
        -- CONCURRENT BLOCK ()
          sig <= (unsigned(sw)) + (1);
          process(clk)
          begin
            if rising_edge(clk) then
              buffer_led <= std_logic_vector(sig);
            end if;
          end process;
        

      

    end;
