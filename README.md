# ai_music
Finds melodies in spillefolk.dk when played  
contains a nodejs player for comparing midi and audio files.  
##Installation##
mddir ai_audio  
cd ai_audio  
git clone https://github.com/oleviolin/ai_music
python3 -m venv venv          
source venv/bin/activate   
pip install -r requirements.txt   
cd player  
npm install  
cd ..  
cp act ..  
cp ast ..  
  
put midi files in ~/ai_audio/mid/cleaned  
Put synthized mp3 files in ~/ai_audio/mp3/first/  
Put solo music mp3 files in ~/ai_audio/mp3/one_kor_sgl/  
Put orchestra music mp3 files in ~/ai_audio/mp3/one_kor/  
File names of midi files and mp3 files must coinside. 
The musical content must be the same.  
   
##Excecute##
#for bulk conversion of mp3 files to Wav  
source/02_convert_to_wav.py  
#for bulk generating visual time data curves  
python source/04_analyze_data.py       
#for for general alignement  
python 07_measure_margins.py   
#for making DTW
python 010_generate_dtw_alignement.py  
