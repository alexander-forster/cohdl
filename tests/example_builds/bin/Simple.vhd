    library ieee;
    use ieee.std_logic_1164.all;
    use ieee.numeric_std.all;
  


    entity Simple is
      port (
          clk : in std_logic;
          sw : in std_logic_vector(15 downto 0);
          led : out std_logic_vector(15 downto 0)
        );
    end Simple;
  


    architecture arch_Simple of Simple is
      function cohdl_bool_to_std_logic(inp: boolean) return std_logic is
      begin
        if inp then
          return('1');
        else
          return('0');
        end if;
      end function cohdl_bool_to_std_logic;
      signal buffer_led : std_logic_vector(15 downto 0);
      signal sig : unsigned(3 downto 0) := unsigned(std_logic_vector'("0000"));
      array array_type is (0 to 127) of std_logic_vector(31 downto 0);
      signal sig_1 : array_type;
      signal sig_2 : std_logic;
    begin
    -- CONCURRENT BLOCK (buffer assignment)
      led <= buffer_led;
    -- Block ()
        process(clk)
          constant const : 1 := 1;
          variable temp : unsigned(3 downto 0);
          constant const_1 : 1 := 1;
          variable temp_1 : unsigned(3 downto 0);
          constant const_2 : 1 := 1;
        begin
          if rising_edge(clk) then
            temp := (sig) + (const);
            temp_1 := (sig) + (const_1);
            sig_1(to_integer(temp)) <= sig_1(to_integer(temp_1));
            sig_2 <= '1';
          end if;
        end process;
      

    end architecture arch_Simple;
