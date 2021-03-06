B
    [??a?E  ?               @   s?   d Z ddlZddlm  mZ ddlmZ ddlmZ ddlm	Z	m
Z
mZmZmZmZ ddlmZ ddlmZ dd	lmZmZmZmZmZ dd
lmZ ddlZdd? ZG dd? dej?ZG dd? dej?Z G dd? dej?Z!G dd? dej?Z"dd? Z#dS )z#
DETR model and criterion classes.
?    N)?nn)?box_ops)?NestedTensor?nested_tensor_from_tensor_list?accuracy?get_world_size?interpolate?is_dist_avail_and_initialized?   )?build_backbone)?build_matcher)?DETRsegm?PostProcessPanoptic?PostProcessSegm?	dice_loss?sigmoid_focal_loss)?build_transformerc             C   s   t t?d|  |  ? ?}|S )z=initialize conv/fc bias value according to giving probablity.r
   )?float?np?log)Z
prior_probZ	bias_init? r   ?A/home/dell/wjs/transformer/transformer/detr-master/models/detr.py?bias_init_with_prob   s    r   c                   s@   e Zd ZdZd
? fdd?	Zed?dd?Zejj	dd	? ?Z
?  ZS )?DETRz8 This is the DETR module that performs object detection Fc                s?   t ? ??  || _|| _|j}t?||d ?| _tj?	| jj
td?? t||dd?| _t?||?| _tj|j|dd?| _|| _|| _dS )a@   Initializes the model.
        Parameters:
            backbone: torch module of the backbone to be used. See backbone.py
            transformer: torch module of the transformer architecture. See transformer.py
            num_classes: number of object classes
            num_queries: number of object queries, ie detection slot. This is the maximal number of objects
                         DETR can detect in a single image. For COCO, we recommend 100 queries.
            aux_loss: True if auxiliary decoding losses (loss at each decoder layer) are to be used.
        r
   g{?G?z???   ?   )?kernel_sizeN)?super?__init__?num_queries?transformer?d_modelr   ?Linear?class_embed?init?	constant_?biasr   ?MLP?
bbox_embed?	Embedding?query_embed?Conv2d?num_channels?
input_proj?backbone?aux_loss)?selfr.   r    ?num_classesr   r/   ?
hidden_dim)?	__class__r   r   r      s    

zDETR.__init__)?samplesc             C   s^  t |d ttjf?r$t|d ?|d< | ?|d ?\}}tjt?dd? |d D ??dd?df t?dd? |d D ??dd?df gdd?}|?d?}|d ?? \}}|dk	s?t	?| ?
| ?|?|| jj|d |?\}}}	|jd }
| ?|?}| ?|?}|?d??|
ddd?}|d	dd
?f | |d	dd
?f< |?? }|d |d d?}| j?rZ| ?||?|d< |S )uk   The forward expects a NestedTensor, which consists of:
               - samples.tensor: batched images, of shape [batch_size x 3 x H x W]
               - samples.mask: a binary mask of shape [batch_size x H x W], containing 1 on padded pixels

            It returns a dict with the following elements:
               - "pred_logits": the classification logits (including no-object) for all queries.
                                Shape= [batch_size x num_queries x (num_classes + 1)]
               - "pred_boxes": The normalized boxes coordinates for all queries, represented as
                               (center_x, center_y, height, width). These values are normalized in [0, 1],
                               relative to the size of each individual image (disregarding possible padding).
                               See PostProcess for information on how to retrieve the unnormalized bounding box.
               - "aux_outputs": Optional, only returned when auxilary losses are activated. It is a list of
                                dictionnaries containing the two above keys for each decoder layer.
        r   c             S   s   g | ]}|d  ?qS )?sizer   )?.0?instr   r   r   ?
<listcomp>E   s    z DETR.forward.<locals>.<listcomp>r
   Nc             S   s   g | ]}|d  ?qS )r5   r   )r6   r7   r   r   r   r8   F   s    ?????)?dim.?   )?pred_logits?
pred_boxes?aux_outputs)?
isinstance?list?torch?Tensorr   r.   ?stack?	unsqueeze?	decompose?AssertionErrorr    r-   r*   ?weight?shaper#   r(   ?repeat?sigmoidr/   ?_set_aux_loss)r0   r4   ?features?posZh_w?src?mask?hs?points?memoryZnum_decoder?outputs_class?outputs_coord?outr   r   r   ?forward2   s&    &,
&


 zDETR.forwardc             C   s$   dd? t |d d? |d d? ?D ?S )Nc             S   s   g | ]\}}||d ??qS ))r<   r=   r   )r6   ?a?br   r   r   r8   `   s   z&DETR._set_aux_loss.<locals>.<listcomp>r9   )?zip)r0   rS   rT   r   r   r   rK   [   s    zDETR._set_aux_loss)F)?__name__?
__module__?__qualname__?__doc__r   r   rV   rA   ?jit?unusedrK   ?__classcell__r   r   )r3   r   r      s   )r   c                   sj   e Zd ZdZ? fdd?Zddd?Ze?? dd? ?Zd	d
? Z	dd? Z
dd? Zdd? Zdd? Zdd? Z?  ZS )?SetCriteriona   This class computes the loss for DETR.
    The process happens in two steps:
        1) we compute hungarian assignment between ground truth boxes and the outputs of the model
        2) we supervise each pair of matched ground-truth / prediction (supervise class and box)
    c                sR   t ? ??  || _|| _|| _|| _|| _t?| jd ?}| j|d< | ?	d|? dS )a   Create the criterion.
        Parameters:
            num_classes: number of object categories, omitting the special no-object category
            matcher: module able to compute a matching between targets and proposals
            weight_dict: dict containing as key the names of the losses and as values their relative weight.
            eos_coef: relative classification weight applied to the no-object category
            losses: list of all the losses to be applied. See get_loss for list of available losses.
        r
   r9   ?empty_weightN)
r   r   r1   ?matcher?weight_dict?eos_coef?lossesrA   ?ones?register_buffer)r0   r1   rc   rd   re   rf   rb   )r3   r   r   r   j   s    	

zSetCriterion.__init__Tc             C   s?   d|kst ?|d }| ?|?}t?dd? t||?D ??}tj|jdd? | jtj|j	d?}	||	|< t
?|?dd?|	| j?}
d|
i}|r?d	t|| |?d
  |d< |S )z?Classification loss (NLL)
        targets dicts must contain the key "labels" containing a tensor of dim [nb_target_boxes]
        r<   c             S   s    g | ]\}\}}|d  | ?qS )?labelsr   )r6   ?t?_?Jr   r   r   r8   ?   s    z,SetCriterion.loss_labels.<locals>.<listcomp>Nr;   )?dtype?devicer
   ?loss_ce?d   r   ?class_error)rF   ?_get_src_permutation_idxrA   ?catrY   ?fullrH   r1   ?int64rn   ?F?cross_entropy?	transposerb   r   )r0   ?outputs?targets?indices?	num_boxesr   Z
src_logits?idxZtarget_classes_oZtarget_classesro   rf   r   r   r   ?loss_labels}   s    
zSetCriterion.loss_labelsc             C   sd   |d }|j }tjdd? |D ?|d?}|?d?|jd d k?d?}t?|?? |?? ?}	d|	i}
|
S )z? Compute the cardinality error, ie the absolute error in the number of predicted non-empty boxes
        This is not really a loss, it is intended for logging purposes only. It doesn't propagate gradients
        r<   c             S   s   g | ]}t |d  ??qS )ri   )?len)r6   ?vr   r   r   r8   ?   s    z1SetCriterion.loss_cardinality.<locals>.<listcomp>)rn   r9   r
   Zcardinality_error)	rn   rA   ?	as_tensor?argmaxrH   ?sumrv   ?l1_lossr   )r0   ry   rz   r{   r|   r<   rn   Ztgt_lengthsZ	card_predZcard_errrf   r   r   r   ?loss_cardinality?   s    zSetCriterion.loss_cardinalityc          	   C   s?   d|kst ?| ?|?}|d | }tjdd? t||?D ?dd?}tj||dd?}i }	|?? | |	d< d	t?t	?
t	?|?t	?|??? }
|
?? | |	d
< |	S )a6  Compute the losses related to the bounding boxes, the L1 regression loss and the GIoU loss
           targets dicts must contain the key "boxes" containing a tensor of dim [nb_target_boxes, 4]
           The target boxes are expected in format (center_x, center_y, w, h), normalized by the image size.
        r=   c             S   s    g | ]\}\}}|d  | ?qS )?boxesr   )r6   rj   rk   ?ir   r   r   r8   ?   s    z+SetCriterion.loss_boxes.<locals>.<listcomp>r   )r:   ?none)?	reduction?	loss_bboxr
   ?	loss_giou)rF   rr   rA   rs   rY   rv   r?   r?   ?diagr   ?generalized_box_iou?box_cxcywh_to_xyxy)r0   ry   rz   r{   r|   r}   Z	src_boxesZtarget_boxesr?   rf   r?   r   r   r   ?
loss_boxes?   s    

zSetCriterion.loss_boxesc             C   s?   d|kst ?| ?|?}| ?|?}|d }|| }dd? |D ?}t|??? \}	}
|	?|?}	|	| }	t|dd?df |	jdd? ddd?}|dd?d	f ?d
?}|	?d
?}	|	?	|j?}	t
||	|?t||	|?d?}|S )z?Compute the losses related to the masks: the focal loss and the dice loss.
           targets dicts must contain the key "masks" containing a tensor of dim [nb_target_boxes, h, w]
        Z
pred_masksc             S   s   g | ]}|d  ?qS )?masksr   )r6   rj   r   r   r   r8   ?   s    z+SetCriterion.loss_masks.<locals>.<listcomp>N??????bilinearF)r5   ?mode?align_cornersr   r
   )?	loss_mask?	loss_dice)rF   rr   ?_get_tgt_permutation_idxr   rE   ?tor   rH   ?flatten?viewr   r   )r0   ry   rz   r{   r|   ?src_idx?tgt_idxZ	src_masksr?   Ztarget_masks?validrf   r   r   r   ?
loss_masks?   s"    





zSetCriterion.loss_masksc             C   s4   t ?dd? t|?D ??}t ?dd? |D ??}||fS )Nc             S   s    g | ]\}\}}t ?||??qS r   )rA   ?	full_like)r6   r?   rN   rk   r   r   r   r8   ?   s    z9SetCriterion._get_src_permutation_idx.<locals>.<listcomp>c             S   s   g | ]\}}|?qS r   r   )r6   rN   rk   r   r   r   r8   ?   s    )rA   rs   ?	enumerate)r0   r{   ?	batch_idxr?   r   r   r   rr   ?   s    z%SetCriterion._get_src_permutation_idxc             C   s4   t ?dd? t|?D ??}t ?dd? |D ??}||fS )Nc             S   s    g | ]\}\}}t ?||??qS r   )rA   r?   )r6   r?   rk   ?tgtr   r   r   r8   ?   s    z9SetCriterion._get_tgt_permutation_idx.<locals>.<listcomp>c             S   s   g | ]\}}|?qS r   r   )r6   rk   r?   r   r   r   r8   ?   s    )rA   rs   r?   )r0   r{   r?   r?   r   r   r   r?   ?   s    z%SetCriterion._get_tgt_permutation_idxc             K   sD   | j | j| j| jd?}||ks.td|? d???|| ||||f|?S )N)ri   ?cardinalityr?   r?   zdo you really want to compute z loss?)r~   r?   r?   r?   rF   )r0   ?lossry   rz   r{   r|   ?kwargsZloss_mapr   r   r   ?get_loss?   s    
zSetCriterion.get_lossc          
      s@  dd? |? ? D ?}| ?||?}tdd? |D ??}tj|gtjtt|?? ??j	d?}t
? rdtj?|? tj|t?  dd??? }i }x&| jD ]}|?| ?|||||?? q?W d|k?r<x?t|d ?D ]x\? }| ?||?}xb| jD ]X}|d	kr?q?i }	|d
kr?ddi}	| j|||||f|	?}
? fdd?|
? ? D ?}
|?|
? q?W q?W |S )aS   This performs the loss computation.
        Parameters:
             outputs: dict of tensors, see the output specification of the model for the format
             targets: list of dicts, such that len(targets) == batch_size.
                      The expected keys in each dict depends on the losses applied, see each loss' doc
        c             S   s   i | ]\}}|d kr||?qS )r>   r   )r6   ?kr?   r   r   r   ?
<dictcomp>?   s    z(SetCriterion.forward.<locals>.<dictcomp>c             s   s   | ]}t |d  ?V  qdS )ri   N)r   )r6   rj   r   r   r   ?	<genexpr>?   s    z'SetCriterion.forward.<locals>.<genexpr>)rm   rn   r
   )?minr>   r?   ri   r   Fc                s    i | ]\}}||d ? ? ? ?qS )rk   r   )r6   r?   r?   )r?   r   r   r?     s    )?itemsrc   r?   rA   r?   r   ?next?iter?valuesrn   r	   ?distributed?
all_reduce?clampr   ?itemrf   ?updater?   r?   )r0   ry   rz   Zoutputs_without_auxr{   r|   rf   r?   r>   r?   Zl_dictr   )r?   r   rV   ?   s.    "
zSetCriterion.forward)T)rZ   r[   r\   r]   r   r~   rA   ?no_gradr?   r?   r?   rr   r?   r?   rV   r`   r   r   )r3   r   ra   d   s   

ra   c               @   s    e Zd ZdZe?? dd? ?ZdS )?PostProcesszQ This module converts the model's output into the format expected by the coco apic             C   s?   |d |d  }}t |?t |?ks&t?|jd dks8t?t?|d?}|ddd?f ?d?\}}t?|?}|?d?\}	}
t	j
|
|	|
|	gdd?}||dd?ddd?f  }d	d
? t|||?D ?}|S )a?   Perform the computation
        Parameters:
            outputs: raw outputs of the model
            target_sizes: tensor of dimension [batch_size x 2] containing the size of each images of the batch
                          For evaluation, this must be the original image size (before any data augmentation)
                          For visualization, this should be the image size after data augment, but before padding
        r<   r=   r
   r;   r9   .N)r:   c             S   s   g | ]\}}}|||d ??qS ))?scoresri   r?   r   )r6   ?s?lrX   r   r   r   r8   -  s    z'PostProcess.forward.<locals>.<listcomp>)r   rF   rH   rv   ?softmax?maxr   r?   ?unbindrA   rC   rY   )r0   ry   ?target_sizesZ
out_logits?out_bbox?probr?   ri   r?   ?img_h?img_wZ	scale_fct?resultsr   r   r   rV     s    	
zPostProcess.forwardN)rZ   r[   r\   r]   rA   r?   rV   r   r   r   r   r?     s   r?   c                   s(   e Zd ZdZ? fdd?Zdd? Z?  ZS )r'   z5 Very simple multi-layer perceptron (also called FFN)c                sJ   t ? ??  || _|g|d  }t?dd? t|g| ||g ?D ??| _d S )Nr
   c             s   s   | ]\}}t ?||?V  qd S )N)r   r"   )r6   ?nr?   r   r   r   r?   9  s    zMLP.__init__.<locals>.<genexpr>)r   r   ?
num_layersr   ?
ModuleListrY   ?layers)r0   ?	input_dimr2   Z
output_dimr?   ?h)r3   r   r   r   5  s    
zMLP.__init__c             C   s@   x:t | j?D ],\}}|| jd k r0t?||??n||?}qW |S )Nr
   )r?   r?   r?   rv   ?relu)r0   ?xr?   ?layerr   r   r   rV   ;  s    (zMLP.forward)rZ   r[   r\   r]   r   rV   r`   r   r   )r3   r   r'   2  s   r'   c                sx  | j dkrdnd}| j dkr d}t?| j?}t| ?}t| ?}t|||| j| jd?}| jrjt	|| j
d k	d?}t| ?}d| jd?}| j|d< | jr?| j|d	< | j|d
< | jr?i }x2t| jd ?D ] ? |?? fdd?|?? D ?? q?W |?|? dddg}	| j?r|	dg7 }	t|||| j|	d?}
|
?|? dt? i}| j?rnt? |d< | j dk?rndd? td?D ?}t|dd?|d< ||
|fS )N?cocor   ?coco_panoptic)r1   r   r/   )Zfreeze_detrr
   )ro   r?   r?   r?   r?   c                s    i | ]\}}||d ? ? ? ?qS )rk   r   )r6   r?   r?   )r?   r   r   r?   h  s    zbuild.<locals>.<dictcomp>ri   r?   r?   r?   )rc   rd   re   rf   ?bbox?segmc             S   s   i | ]}|d k|?qS )?Z   r   )r6   r?   r   r   r   r?   u  s    ??   g333333??)?	threshold?panoptic)?dataset_filerA   rn   r   r   r   r   r/   r?   r   ?frozen_weightsr   Zbbox_loss_coefZgiou_loss_coefZmask_loss_coefZdice_loss_coef?rangeZ
dec_layersr?   r?   ra   re   r?   r?   r   r   )?argsr1   rn   r.   r    ?modelrc   rd   Zaux_weight_dictrf   ?	criterion?postprocessorsZis_thing_mapr   )r?   r   ?buildA  sL    	




 





r?   )$r]   rA   Ztorch.nn.functionalr   ?
functionalrv   ?utilr   ?	util.miscr   r   r   r   r   r	   r.   r   rc   r   ?segmentationr   r   r   r   r   r    r   ?numpyr   r   ?Moduler   ra   r?   r'   r?   r   r   r   r   ?<module>   s"    J 0