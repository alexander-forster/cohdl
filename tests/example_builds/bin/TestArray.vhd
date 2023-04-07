    library ieee;
    use ieee.std_logic_1164.all;
    use ieee.numeric_std.all;
  


    entity TestArray is
      port (
          clk : in std_logic;
          index : in unsigned(3 downto 0)
        );
    end TestArray;
  


    architecture arch_TestArray of TestArray is
      type array_declaration is array (0 to 15) of std_logic_vector(7 downto 0);
      signal sig : array_declaration;
      type array_declaration_1 is array (0 to 31) of std_logic;
      signal sig_1 : array_declaration_1;
    begin
    -- CONCURRENT BLOCK (buffer assignment)
    -- Block ()
        process(clk)
        begin
          if rising_edge(clk) then
            sig(to_integer(index)) <= "00000000";
            sig_1(to_integer(index)) <= '0';
          end if;
        end process;
      

    end;
