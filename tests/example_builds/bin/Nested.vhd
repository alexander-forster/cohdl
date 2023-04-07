    library ieee;
    use ieee.std_logic_1164.all;
    use ieee.numeric_std.all;
  


    entity Nested is
      port (
          clk : in std_logic;
          sw : in std_logic_vector(15 downto 0);
          led : out std_logic_vector(15 downto 0);
          sseg_ca : out std_logic_vector(6 downto 0);
          sseg_an : out std_logic_vector(7 downto 0)
        );
    end Nested;
  


    architecture arch_Nested of Nested is
      signal buffer_led : std_logic_vector(15 downto 0);
      signal buffer_sseg_ca : std_logic_vector(6 downto 0);
      signal buffer_sseg_an : std_logic_vector(7 downto 0);
      type state_type is (s, s_1);
      signal state : state_type := s;
    begin
    -- CONCURRENT BLOCK (buffer assignment)
      led <= buffer_led;
      sseg_ca <= buffer_sseg_ca;
      sseg_an <= buffer_sseg_an;
    -- Block ()
        process(clk)
        begin
          if rising_edge(clk) then
            case state is
              when s =>
                if sw(0) = '1' then
                  buffer_led(0) <= '1';
                  state <= s_1;
                end if;
              when s_1 =>
                if sw(1) = '1' then
                  state <= s;
                  buffer_led(1) <= '1';
                end if;
              when others =>
                null;
            end case;
          end if;
        end process;
      

    end;
