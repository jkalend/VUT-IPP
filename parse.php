<?php

ini_set('display_errors', 'stderr');

class ArgParse {
    # Class for parsing the command line arguments
    private $stats_files, $stat_names;

    function __construct($argv) {
        # parses the command line arguments when initialized
        $this->stats_files = [];
        $this->stat_names = [];
        if (in_array("--help", $argv)) {
            if (count($argv) > 2) {
                fwrite(STDERR ,"Invalid number of arguments\n");
                $this->usage();
                exit(10);
            }
            $this->usage();
            exit(0);
        }

        # Parses the stats arguments
        for ($i = 1; $i < count($argv); $i++) {
            if (preg_match('/^--stats=/', $argv[$i])) {
                $name = preg_replace('/^--stats=/', '', $argv[$i]);
                if (in_array($name, $this->stat_names)) {
                    fwrite(STDERR, "Duplicate stats file name\n");
                    exit(12);
                }
                $this->stats_files[]["stats"] = $name;
                $this->stat_names[] = $name;
            } elseif (preg_match('/^--stats$/', $argv[$i])) {
                if ($i + 1 >= count($argv)) {
                    fwrite(STDERR, "Missing stats file name\n");
                    $this->usage();
                    exit(10);
                }
                $name = $argv[++$i];
                if (in_array($name, $this->stat_names)) {
                    fwrite(STDERR, "Duplicate stats file name\n");
                    $this->usage();
                    exit(12);
                } elseif (preg_match('/^--/', $name)) {
                    fwrite(STDERR, "Invalid stats file name\n");
                    $this->usage();
                    exit(10);
                }
                $this->stats_files[]["stats"] = $name;
                $this->stat_names[] = $name;
            } elseif (preg_match('/^--loc$/', $argv[$i]) && count($this->stats_files) != 0) {
                $this->stats_files[count($this->stats_files) - 1][] = "loc";
            } elseif (preg_match('/^--comments$/', $argv[$i]) && count($this->stats_files) != 0) {
                $this->stats_files[count($this->stats_files) - 1][] = "comments";
            } elseif (preg_match('/^--labels$/', $argv[$i]) && count($this->stats_files) != 0) {
                $this->stats_files[count($this->stats_files) - 1][] = "labels";
            } elseif (preg_match('/^--jumps$/', $argv[$i]) && count($this->stats_files) != 0) {
                $this->stats_files[count($this->stats_files) - 1][] = "jumps";
            } elseif (preg_match('/^--fwjumps$/', $argv[$i]) && count($this->stats_files) != 0) {
                $this->stats_files[count($this->stats_files) - 1][] = "fwjumps";
            } elseif (preg_match('/^--backjumps$/', $argv[$i]) && count($this->stats_files) != 0) {
                $this->stats_files[count($this->stats_files) - 1][] = "backjumps";
            } elseif (preg_match('/^--badjumps$/', $argv[$i]) && count($this->stats_files) != 0) {
                $this->stats_files[count($this->stats_files) - 1][] = "badjumps";
            } elseif (preg_match('/^--frequent$/', $argv[$i]) && count($this->stats_files) != 0) {
                $this->stats_files[count($this->stats_files) - 1][] = "frequent";
            } elseif (preg_match('/^--print=/', $argv[$i]) && count($this->stats_files) != 0) {
                $this->stats_files[count($this->stats_files) - 1][] = ["print", preg_replace('/^--print=/', '', $argv[$i])];
            } elseif (preg_match('/^--print$/', $argv[$i]) && count($this->stats_files) != 0) {
                if ($i + 1 >= count($argv)) {
                    fwrite(STDERR, "Missing print argument\n");
                    $this->usage();
                    exit(10);
                }
                $this->stats_files[count($this->stats_files) - 1][] = ["print", $argv[++$i]];
            } elseif (preg_match('/^--eol$/', $argv[$i]) && count($this->stats_files) != 0) {
                $this->stats_files[count($this->stats_files) - 1][] = "eol";
            } else {
                fwrite(STDERR, "Invalid command line argument\n");
                $this->usage();
                exit(10);
            }
        }
    }

    public function fetch_stats() {
        # Getter for the stats files
        return $this->stats_files;
    }

    private function usage() {
        # Prints the usage
        fwrite(STDOUT ,"Usage: parse.php [--help] [--stats FILE] [--stats=FILE]
         [--loc] [--comments] [--labels] [--jumps] [--fwjumps] [--backjumps]
         [--badjumps] [--frequent] [--print=FILE] [--print FILE] [--eol]
         \nAccepts file contents on stdin and outputs XML to stdout.
         \n--stats have to be specified before any other stats argument.\n");
    }
}

class XMLCreator {
    # Class for creating the XML output
    private $xml, $order;

    function __construct() {
        $this->order = 1;
        $this->xml = new SimpleXMLElement('<?xml version="1.0" encoding="UTF-8"?><program language="IPPcode23"></program>');
    }

    public function addXML($name, $args) {
        # adds instruction and its arguments to the xml
        $xml_in = $this->xml->addChild('instruction');
        $xml_in->addAttribute('order', $this->order++);
        $xml_in->addAttribute('opcode', $name);
        foreach ($args as $i => $arg) {
            # replaces the special characters with their XML entities
            $arg = preg_replace('/&/', '&amp;', $arg);
            $arg = preg_replace('/</', '&lt;', $arg);
            $arg = preg_replace('/>/', '&gt;', $arg);
            $xml_arg = $xml_in->addChild('arg' . ($i + 1), $arg['value']);
            $xml_arg->addAttribute('type', $arg['type']);
        }
        return 1;
    }

    public function outputXML() {
        # outputs the XML on stdout
        echo $this->xml->asXML();
    }
}

class Stats {
    # Class used to gather and write the stats
    private $labels, $jumps, $fwjumps, $backjumps, $badjumps, $frequent,
        $jump_istr, $jump_dirs, $last_call, $stats, $loc, $comments;

    function __construct($stats) {
        $this->stats = $stats;
        $this->loc = 0;
        $this->comments = 0;
        $this->labels = [];
        $this->jumps = 0;
        $this->fwjumps = 0;
        $this->backjumps = 0;
        $this->badjumps = 0;
        $this->frequent = [];
        $this->jump_istr = ["CALL", "JUMP", "JUMPIFEQ", "JUMPIFNEQ", "RETURN"];
        $this->jump_dirs = [];
        $this->last_call = [];
    }

    function __destruct() {
        # writes the stats to the files when the parser is done
        $file = false;
        foreach ($this->stats as $i) {
            foreach ($i as $x => $stat) {
                if ($x == "stats") {
                    $file = fopen($stat, "w");
                    continue;
                }
                if (is_array($stat)) {
                    fwrite($file, $stat[1] . "\n");
                    continue;
                }

                if ($stat == "loc") {
                    fwrite($file, $this->loc . "\n");
                } elseif ($stat == "comments") {
                    fwrite($file, $this->comments . "\n");
                } elseif ($stat == "labels") {
                    fwrite($file, count($this->labels) . "\n");
                } elseif ($stat == "jumps") {
                    fwrite($file, $this->jumps . "\n");
                } elseif ($stat == "fwjumps") {
                    fwrite($file, $this->fwjumps . "\n");
                } elseif ($stat == "backjumps") {
                    fwrite($file, $this->backjumps . "\n");
                } elseif ($stat == "badjumps") {
                    $this->get_badjumps();
                    fwrite($file, $this->badjumps . "\n");
                } elseif ($stat == "frequent") {
                    arsort($this->frequent);
                    $comma = count($this->frequent);
                    foreach ($this->frequent as $instr => $count) {
                        fwrite($file, $instr);
                        if (--$comma > 0) fwrite($file, ",");
                    }
                    fwrite($file, "\n");
                } elseif ($stat == "eol") {
                    fwrite($file, "\n");
                } else {
                    exit(10);
                }
            }
            if (is_resource($file)) fclose($file);
        }
    }

    private function get_badjumps() {
        # counts the bad jumps and subtracts them from the speculative forward jumps
        foreach ($this->jump_dirs as $dir => $jumps) {
            if (!in_array($dir, $this->labels)) {
                $this->badjumps += $jumps;
                $this->fwjumps -= $jumps;
            }
        }
    }

    public function gather($instr, $args) {
        # Gathers the stats from the instructions
        $this->loc++;

        if (!array_key_exists($instr, $this->frequent))
            $this->frequent[$instr] = 0;
        else
            $this->frequent[$instr]++;


        if ($instr == 'LABEL') {
            if (in_array($args[0]["value"], $this->labels)) return;
            $this->labels[] = $args[0]["value"];
            return;
        }

        if (in_array($instr, $this->jump_istr)) {
            $this->jumps++;
            if ($instr == 'RETURN') {
                $direction = array_pop($this->last_call);
                if ($direction == -1)
                    $this->fwjumps++;
                else
                    $this->backjumps++;
                return;
            }

            if (!array_key_exists($args[0]["value"], $this->jump_dirs))
                $this->jump_dirs[$args[0]["value"]] = 1;
            else
                $this->jump_dirs[$args[0]["value"]]++;

            if (in_array($args[0]["value"], $this->labels)) {
                $this->backjumps++;
                if ($instr == 'CALL')
                    $this->last_call[] = -1;
            } else {
                $this->fwjumps++;
                if ($instr == 'CALL')
                    $this->last_call[] = 1;
            }
        }
    }

    public function inc_comments() {
        # increments the number of comments
        $this->comments++;
    }
}

class Parser {
    # Class used to parse the input
    private $zeros, $only_label, $symb_only, $var_only, $var_symb, $var_type, $var_symb_symb,
        $label_symb_symb, $types, $args, $xml, $argparse, $instr, $stats;

    function __construct($argv) {
        $this->xml = new XMLCreator();
        $this->argparse = new ArgParse($argv);
        $this->stats = new Stats($this->argparse->fetch_stats());

        # read the header
        while (true) {
            if (feof(STDIN)) {
                fwrite(STDERR ,"Missing header\n");
                exit(21);
            }
            $line = trim(fgets(STDIN));
            if (strlen($line) == 0) continue;

            if (str_starts_with($line, '#')) {
                $this->stats->inc_comments();
                continue;
            }

            $line = explode('#', strtolower($line));
            if (count($line) >= 2) $this->stats->inc_comments();

            if (preg_match('/^\.ippcode23$/', trim($line[0]))) {
                break;
            } else {
                fwrite(STDERR ,"Invalid header\n");
                exit(21);
            }
        }

        # initialize the instruction arrays
        $this->types = ["var", "int", "bool", "string", "nil"];
        $this->zeros = ["CREATEFRAME", "PUSHFRAME", "POPFRAME", "RETURN", "BREAK"];
        $this->only_label = ["CALL", "LABEL", "JUMP"];
        $this->symb_only = ["PUSHS", "EXIT", "DPRINT", "WRITE"];
        $this->var_only = ["DEFVAR", "POPS"];
        $this->var_symb = ["MOVE", "INT2CHAR", "STRLEN", "TYPE", "NOT"];
        $this->var_type = ["READ"];
        $this->var_symb_symb = ["ADD", "SUB", "MUL", "IDIV", "LT", "GT", "EQ", "AND", "OR", "STRI2INT", "CONCAT", "GETCHAR", "SETCHAR"];
        $this->label_symb_symb = ["JUMPIFEQ", "JUMPIFNEQ"];
    }

    private function parseArg($arg) {
        # Parses the argument and returns the type and value
        if (preg_match('/^int@/', $arg)) {
            $arg = preg_replace('/^int@/', '', $arg);
            if (preg_match('/^[-+]?((0|([1-9][0-9]*(_[0-9]+)*))|(0[xX][0-9a-fA-F]+(_[0-9a-fA-F]+)*)|(0[oO]?[0-7]+(_[0-7]+)*))$/', $arg)) {
                return ['type' => 'int', 'value' => $arg];
            }
        } elseif (preg_match('/^bool@/', $arg)) {
            $arg = preg_replace('/^bool@/', '', $arg);
            if (preg_match('/^(true|false)$/', $arg)) {
                return ['type' => 'bool', 'value' => $arg];
            }
        } elseif (preg_match('/^string@/', $arg)) {
            $arg = preg_replace('/^string@/', '', $arg);
            if (preg_match('/^([^#\\\]|(\\\\[0-9]{3}))*$/', $arg)) {
                return ['type' => 'string', 'value' => $arg];
            }
        } elseif (preg_match('/^nil@nil$/', $arg)) {
            return ['type' => 'nil', 'value' => 'nil'];
        } elseif (preg_match('/^(GF|LF|TF)@/', $arg)) {
            $pre = preg_split('/@/', $arg);
            $arg = preg_replace('/^(GF|LF|TF)@/', '', $arg);
            if (preg_match('/^([a-zA-Z]|[_$&%*!?-])[a-zA-Z0-9_$&%*!?-]*$/', $arg)) {
                return ['type' => 'var', 'value' => $pre[0] . "@" . $arg];
            }
        } elseif (preg_match('/^(int|bool|string)$/', $arg)) {
            return ['type' => 'type', 'value' => $arg];
        } elseif (preg_match('/^([a-zA-Z]|[_$&%*!?-])[a-zA-Z0-9_$&%*!?-]*$/', $arg)) {
            if (preg_match('/^([a-zA-Z]|[_$&%*!?-])[a-zA-Z0-9_$&%*!?-]*$/', $arg)) {
                return ['type' => 'label', 'value' => $arg];
            }
        }
        fwrite(STDERR ,"Invalid argument\n");
        exit(23);
    }

    private function check_ops($x) {
        # check if the instruction arguments are of a valid type and add them to the XML
        switch ($x) {
            case "var":
                if ($this->args[0]['type'] != 'var') break;
                $this->stats->gather($this->instr, $this->args);
                return $this->xml->addXML($this->instr, $this->args);
            case "symb":
                if (!in_array($this->args[0]['type'], $this->types)) break;
                $this->stats->gather($this->instr, $this->args);
                return $this->xml->addXML($this->instr, $this->args);
            case "label":
                if ($this->args[0]['type'] != 'label') break;
                $this->stats->gather($this->instr, $this->args);
                return $this->xml->addXML($this->instr, $this->args);
            case "var_symb":
                if ($this->args[0]['type'] != 'var' || !in_array($this->args[1]['type'], $this->types)) break;
                $this->stats->gather($this->instr, $this->args);
                return $this->xml->addXML($this->instr, $this->args);
            case "var_type":
                if ($this->args[0]['type'] != 'var' || $this->args[1]['type'] != 'type') break;
                $this->stats->gather($this->instr, $this->args);
                return $this->xml->addXML($this->instr, $this->args);
            case "var_symb_symb":
                if ($this->args[0]['type'] != 'var' || !in_array($this->args[1]['type'], $this->types) || !in_array($this->args[2]['type'], $this->types)) break;
                $this->stats->gather($this->instr, $this->args);
                return $this->xml->addXML($this->instr, $this->args);
            case "label_symb_symb":
                if ($this->args[0]['type'] != 'label' || !in_array($this->args[1]['type'], $this->types) || !in_array($this->args[2]['type'], $this->types)) break;
                $this->stats->gather($this->instr, $this->args);
                return $this->xml->addXML($this->instr, $this->args);
            default:
                break;
        }
        fwrite(STDERR ,"Invalid operands\n");
        exit(23);
    }

    private function invalid_args() {
        fwrite(STDERR ,"Invalid number of instruction arguments\n");
        exit(23);
    }
    
    public function parse() {
        # main function for parsing the input
        while ($line = fgets(STDIN)) {

            # skips the comments and empty lines
            $line = trim($line);
            if (strlen($line) == 0) continue;
            if (str_starts_with($line, '#')) {
                $this->stats->inc_comments();
                continue;
            }

            # splits the actual code from comments on the line
            $line = explode('#', $line);
            if (count($line) >= 2) $this->stats->inc_comments();

            # splits the line into an array of arguments
            $elements = preg_split('/\s+/', trim($line[0]));
            $this->instr = strtoupper($elements[0]);

            # parses the arguments of the instructions and sets their types and values
            $this->args = array_map(array($this, 'parseArg'), array_slice($elements,1));

            # checks if the instruction opcode is valid and if the number of arguments is correct
            if (in_array($this->instr, $this->zeros)) {
                if (count($elements) != 1) $this->invalid_args();
                $this->stats->gather($this->instr, $this->args);
                $this->xml->addXML($this->instr, $this->args);
            } elseif (in_array($this->instr, $this->only_label)) {
                if (count($elements) != 2) $this->invalid_args();
                $this->check_ops("label");
            } elseif (in_array($this->instr, $this->var_only)) {
                if (count($elements) != 2) $this->invalid_args();
                $this->check_ops("var");
            } elseif (in_array($this->instr, $this->symb_only)) {
                if (count($elements) != 2) $this->invalid_args();
                $this->check_ops("symb");
            } elseif (in_array($this->instr, $this->var_symb)) {
                if (count($elements) != 3) $this->invalid_args();
                $this->check_ops("var_symb");
            } elseif (in_array($this->instr, $this->var_type)) {
                if (count($elements) != 3) $this->invalid_args();
                $this->check_ops("var_type");
            } elseif (in_array($this->instr, $this->var_symb_symb)) {
                if (count($elements) != 4) $this->invalid_args();
                $this->check_ops("var_symb_symb");
            } elseif (in_array($this->instr, $this->label_symb_symb)) {
                if (count($elements) != 4) $this->invalid_args();
                $this->check_ops("label_symb_symb");
            } elseif ($this->instr == ".IPPCODE23") {
                fwrite(STDERR ,"Invalid additional header\n");
                exit(22);
            } else {
                fwrite(STDERR ,"Invalid instruction\n");
                exit(22);
            }
        }
        $this->xml->outputXML();
    }
}

$parser = new Parser($argv);
$parser->parse();
