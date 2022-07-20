DS-DETR
## Environment
Ubuntu 18.0.4, Python 3.9, Pytorch=1.7.0.

## Model weight
链接: https://pan.baidu.com/s/1aYhTjqOcXMkCHWEP67Wg4A?pwd=1234 提取码: 1234

## Evaluating a model

python main.py --dataset_file "coco" --coco_path "data/coco" --epoch 100 --lr_backbone=1e-5 --batch_size=2 --num_workers=4 --output_dir="outputs"  --lr 1e-4 --lr_drop 80 --pretrain checkpoint0099.pth --masks  --enc_rpe2d rpe-2.0-product-ctx-1-k --dynamic_scale type3 --eval



## Training

python main.py --dataset_file "coco" --coco_path "data/coco" --epoch 100 --lr_backbone=1e-5 --batch_size=2 --num_workers=4 --output_dir="outputs"  --lr 1e-4 --lr_drop 80 --pretrain checkpoint0098.pth --masks  --enc_rpe2d rpe-2.0-product-ctx-1-k --dynamic_scale type3

