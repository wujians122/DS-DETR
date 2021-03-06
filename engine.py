B
    *?%b$  ?            	   @   s?   d Z ddlZddlZddlZddlmZ ddlZddlZddl	m
Z ddlmZ ddlmZ ddlmZ ddlmZ ddlmZ dejjejjeejjejeed	?d
d?Ze?? dd? ?ZdS )z*
Train and eval functions used in main.py
?    N)?Iterable)?CocoEvaluator)?PanopticEvaluator)?compute_fps)?compute_params)?compute_gflops_and_model_size)?model?	criterion?data_loader?	optimizer?device?epoch?max_normc                s.  | ? ?  |? ?  tjdd?}|?dtjddd?? |?dtjddd?? d	?|?}d
}	?x?|?||	|?D ?]?\}
}|
?? ?}
? fdd?|D ?}| |
?}t| |
? d?}t	| |
?\}}t
| ?}|d d d }td|? td?||?? td?||?? |||??|j?t??fdd???? D ??}t???}dd? |?? D ?}?fdd?|?? D ?}t|?? ?}|?? }t?|??s?td?|?? t|? t?d? |??  |??  |dk?r?tjj?| ?? |? |??  |jf d|i||?? |j|d d? |j|jd d d? qhW |? ?  td|? dd? |j!?? D ?S )Nz  )?	delimiter?lr?   z{value:.6f})?window_size?fmt?class_errorz{value:.2f}zEpoch: [{}]i?  c                s"   g | ]}? fd d?|? ? D ??qS )c                s   i | ]\}}|? ? ?|?qS ? )?to)?.0?k?v)r   r   ?D/home/dell/wjs/transformer/transformer/detr-master/DS-DETR/engine.py?
<dictcomp>   s    z.train_one_epoch.<locals>.<listcomp>.<dictcomp>)?items)r   ?t)r   r   r   ?
<listcomp>   s    z#train_one_epoch.<locals>.<listcomp>)r   g      @i   Zfffffffffffz{:.3f} GFlops - {:.3f} MBz'num_params: {} - size_params: {:.3f} MBc             3   s&   | ]}|?kr? | ?|  V  qd S )Nr   )r   r   )?	loss_dict?weight_dictr   r   ?	<genexpr>.   s    z"train_one_epoch.<locals>.<genexpr>c             S   s   i | ]\}}||? d ??qS )?	_unscaledr   )r   r   r   r   r   r   r   2   s   z#train_one_epoch.<locals>.<dictcomp>c                s&   i | ]\}}|? kr|? |  |?qS r   r   )r   r   r   )r    r   r   r   4   s   zLoss is {}, stopping trainingr   ?loss)r   )r   zAveraged stats:c             S   s   i | ]\}}|j |?qS r   )?
global_avg)r   r   ?meterr   r   r   r   K   s    )"?train?utils?MetricLogger?	add_meter?SmoothedValue?format?	log_everyr   r   r   r   ?printr    ?sum?keys?reduce_dictr   ?values?item?math?isfinite?sys?exit?	zero_grad?backward?torch?nn?clip_grad_norm_?
parameters?step?update?param_groups?synchronize_between_processes?meters)r   r	   r
   r   r   r   r   ?metric_logger?header?
print_freq?samples?targets?outputs?fpsZgflopsZ
model_sizeZ
num_paramsZsize_params?losses?loss_dict_reduced?loss_dict_reduced_unscaled?loss_dict_reduced_scaledZlosses_reduced_scaledZ
loss_valuer   )r   r   r    r   ?train_one_epoch   sV    








rM   c                s,  | ? ?  |? ?  tjdd?}|?dtjddd?? d}t?fdd	?d
D ??}	t||	?}
d }d??? kr?t|j	j
|j	jtj?|d?d?}?x?|?|d|?D ?]?\}}|?? ?}? fdd?|D ?}| ||g?}|||?}|j?t?|?}?fdd?|?? D ?}dd? |?? D ?}|jf dt|?? ?i||?? |j|d d? tjdd? |D ?dd?}?d ||?}d??? k?r?tjdd? |D ?dd?}?d ||||?}dd? t||?D ?}|
d k	?r?|
?|? |d k	r??d |||?}xFt|?D ]:\}}|d ?? }|d?d?}||| d< ||| d < ?q?W |?|? q?W |??  td!|? |
d k	?rR|
??  |d k	?rd|??  |
d k	?r~|
??  |
??  d }|d k	?r?|?? }d"d? |j ?? D ?}|
d k	?r?d??? k?r?|
j!d j"?#? |d#< d??? k?r?|
j!d j"?#? |d$< |d k	?r$|d% |d&< |d' |d(< |d) |d*< ||
fS )+Nz  )r   r   r   z{value:.2f})r   r   zTest:c             3   s   | ]}|? ? ? kr|V  qd S )N)r/   )r   r   )?postprocessorsr   r   r!   W   s    zevaluate.<locals>.<genexpr>)?segm?bboxZpanopticZpanoptic_eval)?
output_diri?  c                s"   g | ]}? fd d?|? ? D ??qS )c                s   i | ]\}}|? ? ?|?qS r   )r   )r   r   r   )r   r   r   r   e   s    z'evaluate.<locals>.<listcomp>.<dictcomp>)r   )r   r   )r   r   r   r   e   s    zevaluate.<locals>.<listcomp>c                s&   i | ]\}}|? kr|? |  |?qS r   r   )r   r   r   )r    r   r   r   m   s   zevaluate.<locals>.<dictcomp>c             S   s   i | ]\}}||? d ??qS )r"   r   )r   r   r   r   r   r   r   o   s   r#   )r   c             S   s   g | ]}|d  ?qS )?	orig_sizer   )r   r   r   r   r   r   v   s    r   )?dimrP   rO   c             S   s   g | ]}|d  ?qS )?sizer   )r   r   r   r   r   r   y   s    c             S   s   i | ]\}}||d  ? ? ?qS )?image_id)r2   )r   ?target?outputr   r   r   r   {   s    rU   Z012dz.png?	file_namezAveraged stats:c             S   s   i | ]\}}|j |?qS r   )r$   )r   r   r%   r   r   r   r   ?   s    Zcoco_eval_bboxZcoco_eval_masks?AllZPQ_allZThingsZPQ_thZStuffZPQ_st)$?evalr'   r(   r)   r*   ?tupler   r/   r   ?dataset?ann_fileZ
ann_folder?os?path?joinr,   r   r    r0   r   r>   r.   r1   r9   ?stack?zip?	enumerater2   r@   r-   ?
accumulate?	summarizerA   ?	coco_eval?stats?tolist)r   r	   rN   r
   ?base_dsr   rQ   rB   rC   Z	iou_types?coco_evaluatorZpanoptic_evaluatorrE   rF   rG   r   rJ   rL   rK   Zorig_target_sizes?resultsZtarget_sizes?resZres_pano?irV   rU   rX   Zpanoptic_resrg   r   )r   rN   r    r   ?evaluateN   s?    













rn   )r   )?__doc__r3   r^   r5   ?typingr   r9   ?numpy?np?	util.misc?miscr'   Zdatasets.coco_evalr   Zdatasets.panoptic_evalr   Zmetrics.modelr   r   r   r:   ?Module?optim?	Optimizerr   ?int?floatrM   ?no_gradrn   r   r   r   r   ?<module>   s   *: