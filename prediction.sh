b=$(date +%e.%m.%y_%H:%M:%S)
name=$(echo "answers_$b.txt")
touch $name
tgpt "предскажи будущее для '${1}' на '${2}', он(она) является '${3}' для CH aka meta.c0wb0y, используй следующие слова словно эти слова выпали при раскладе карт Тарро: '$(echo $(.shortcuts/VANGA.sh) | head -n 1)'" >> $name
tail -n 1 words
echo "Last answer" >> $name
cat $name   
