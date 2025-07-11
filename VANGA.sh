words=$(echo $(python predict.py >> hex.values && tail -n 1 hex.values | echo $(echo $(python prediction.py) | head -n 1))) 
echo $words >> words
echo $words

