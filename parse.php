<?php

$longopts  = array(
    "help",    // No value
);

$options = getopt("", $longopts);
//var_dump($options);
if (count($options) == 0) {
    echo "No options passed";
} else {
    echo "Options passed";
}
?>

