    library ieee;
    use ieee.std_logic_1164.all;
    use ieee.numeric_std.all;
  


    entity ForLoop is
      port (
          clk : in std_logic;
          sw : in std_logic_vector(2 downto 0);
          led : out std_logic_vector(15 downto 0)
        );
    end ForLoop;
  


    architecture arch_ForLoop of ForLoop is
      function cohdl_bool_to_std_logic(inp: boolean) return std_logic is
      begin
        if inp then
          return('1');
        else
          return('0');
        end if;
      end function cohdl_bool_to_std_logic;
      signal buffer_led : std_logic_vector(15 downto 0);
      signal temp : std_logic;
      signal sig : unsigned(5 downto 0) := unsigned(std_logic_vector'("000000"));
    begin
    -- CONCURRENT BLOCK (buffer assignment)
      led <= buffer_led;
    -- Block ()
      -- CONCURRENT BLOCK ()
        with sw(1) select temp <=
          '1' when '1',
          '0' when others;
        sig(0) <= temp;
      

    end architecture arch_ForLoop;
