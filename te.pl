my $base='python rpt.py -r /home/jian/tr -d VSPHERE -j ESX ';
my $basemv='mv /home/jian/tr/Report-2016.11.30.pdf /home/jian/tr/Rpt-';

while (<>) {
  chomp;
  my @cycles=split(':');
  print "$cycles[0] ---- |$cycles[1]|\n";
  my $cmd = $base . " -n $cycles[0] -c $cycles[1]";
  print " ====== $cmd ===== \n";
  system("$cmd");
  my $mv = $basemv . $cycles[0] . '.pdf';
  print " ====== $mv ===== \n";
  #system("$mv");
  print " sleep 5 seconds\n";
  system("sleep 5");
}
