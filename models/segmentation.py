B
    ށb??  ?               @   s6  d Z ddlZddlmZ ddlmZmZ ddlZddlm	Z	 ddl
m	  mZ ddlmZ ddlmZ ddlmZ ddlmZmZmZ yddlmZmZ W n ek
r?   Y nX G d	d
? d
e	j?Zed?dd?ZG dd? de	j?ZG dd? de	j?Zdd? Z de!e!d?dd?Z"G dd? de	j?Z#G dd? de	j?Z$dS )zk
This file provides the definition of the convolutional heads used to predict masks, as well as the losses
?    N)?defaultdict)?List?Optional)?Tensor)?Image)?NestedTensor?interpolate?nested_tensor_from_tensor_list)?id2rgb?rgb2idc                   s,   e Zd Zd? fdd?	Zed?dd?Z?  ZS )?DETRsegmFc                sp   t ? ??  || _|r0x| ?? D ]}|?d? qW |jj|jj }}t|||dd?| _	t
|| dddg|?| _d S )NFg        )?dropouti   i   ?   )?super?__init__?detr?
parameters?requires_grad_?transformer?d_model?nhead?MHAttentionMap?bbox_attention?MaskHeadSmallConv?	mask_head)?selfr   ?freeze_detr?p?
hidden_dimZnheads)?	__class__? ?I/home/dell/wjs/transformer/transformer/detr-master/models/segmentation.pyr      s    
zDETRsegm.__init__)?samplesc             C   s?  t |d ttjf?r$t|d ?|d< | j?|d ?\}}tjt?dd? |d D ??d d ?df t?dd? |d D ??d d ?df gdd?}|?d?}|d j	j
d }|d ?? \}}|d k	s?t?| j?|?}| j?||| jjj|d |?\}	}
}|	j
d }| j?|	?}| j?|	?}|
?d??|ddd?}
|dd d	?f |
 |dd d	?f< |?? }|d |d d
?}| jj?r~| j?||?|d< | j|	d ||d?}| ?|||d	 j	|d j	|d j	g?}|?|| jj|j
d |j
d ?}||d< |S )Nr   c             S   s   g | ]}|d  ?qS )?sizer    )?.0?instr    r    r!   ?
<listcomp>+   s    z$DETRsegm.forward.<locals>.<listcomp>?   c             S   s   g | ]}|d  ?qS )r#   r    )r$   r%   r    r    r!   r&   ,   s    ?????)?dim.?   )?pred_logits?
pred_boxes?aux_outputs)?mask??????
pred_masks)?
isinstance?list?torchr   r	   r   ?backbone?stack?	unsqueeze?tensors?shape?	decompose?AssertionError?
input_projr   ?query_embed?weight?class_embed?
bbox_embed?repeat?sigmoid?aux_loss?_set_aux_lossr   r   ?view?num_queries)r   r"   ?features?pos?h_w?bs?srcr.   Zsrc_proj?hs?points?memory?num_decoder?outputs_class?outputs_coord?out?	bbox_maskZ	seg_masksZoutputs_seg_masksr    r    r!   ?forward%   s2    &,
$
 
& zDETRsegm.forward)F)?__name__?
__module__?__qualname__r   r   rS   ?__classcell__r    r    )r   r!   r      s   r   )?lengthc             C   s$   | ? d??dt|?ddd??dd?S )Nr'   r   )r6   r@   ?int?flatten)?tensorrX   r    r    r!   ?_expandO   s    r\   c                   s6   e Zd ZdZ? fdd?Zeeee d?dd?Z?  ZS )r   zb
    Simple convolutional head, using group norm.
    Upsampling is done using a FPN approach
    c                s?  t ? ??  ||d |d |d |d |d g}tjj||ddd?| _tj?d|?| _tjj||d ddd?| _tj?d|d ?| _	tjj|d |d ddd?| _
tj?d|d ?| _tjj|d |d ddd?| _tj?d|d ?| _tjj|d |d ddd?| _tj?d|d ?| _tjj|d dddd?| _|| _tj?|d	 |d d?| _tj?|d |d d?| _tj?|d |d d?| _xB| ?? D ]6}t|tj??r?tjj|jdd
? tj?|jd	? ?q?W d S )Nr*   ?   ?   ?   ?@   ?   r'   )?paddingr   )?a)r   r   r3   ?nn?Conv2d?lay1?	GroupNorm?gn1?lay2?gn2?lay3?gn3?lay4?gn4?lay5?gn5?out_layr)   ?adapter1?adapter2?adapter3?modulesr1   ?init?kaiming_uniform_r=   ?	constant_?bias)r   r)   Zfpn_dimsZcontext_dimZ
inter_dims?m)r   r    r!   r   Y   s*    
$zMaskHeadSmallConv.__init__)?xrR   ?fpnsc             C   s?  t ?t||jd ?|?dd?gd?}| ?|?}| ?|?}t?|?}| ?	|?}| ?
|?}t?|?}| ?|d ?}|?d?|?d?kr?t||?d?|?d? ?}|tj||jdd ? dd? }| ?|?}| ?|?}t?|?}| ?|d ?}|?d?|?d?k?rt||?d?|?d? ?}|tj||jdd ? dd? }| ?|?}| ?|?}t?|?}| ?|d ?}|?d?|?d?k?r?t||?d?|?d? ?}|tj||jdd ? dd? }| ?|?}| ?|?}t?|?}| ?|?}|S )Nr'   r   r/   ?nearest)r#   ?moder*   )r3   ?catr\   r8   rZ   rf   rh   ?F?reluri   rj   rr   r#   r   rk   rl   rs   rm   rn   rt   ro   rp   rq   )r   r{   rR   r|   Zcur_fpnr    r    r!   rS   t   s<    $















zMaskHeadSmallConv.forward)	rT   rU   rV   ?__doc__r   r   r   rS   rW   r    r    )r   r!   r   S   s   r   c                   s6   e Zd ZdZd
? fdd?	Zdee d?dd	?Z?  ZS )r   zdThis is a 2D attention module, which only returns the attention softmax (no multiplication by value)?        Tc                s?   t ? ??  || _|| _t?|?| _tj|||d?| _tj|||d?| _	tj
?| j	j? tj
?| jj? tj
?| j	j? tj
?| jj? t|| j ?d | _d S )N)ry   g      ??)r   r   ?	num_headsr   rd   ?Dropoutr   ?Linear?q_linear?k_linearrv   ?zeros_ry   ?xavier_uniform_r=   ?float?normalize_fact)r   Z	query_dimr   r?   r   ry   )r   r    r!   r   ?   s    
zMHAttentionMap.__init__N)r.   c             C   s?   | ? |?}t?|| jj?d??d?| jj?}|?|jd |jd | j	| j
| j	 ?}|?|jd | j	| j
| j	 |jd |jd ?}t?d|| j |?}|d k	r?|?|?d??d?td?? tj|?d?dd??|?? ?}| ?|?}|S )	Nr(   r   r'   r/   zbqnc,bnchw->bqnhwz-infr*   )r)   )r?   r?   ?conv2dr?   r=   r6   ry   rD   r8   r?   r   r3   ?einsumr?   ?masked_fill_r?   ?softmaxrZ   r#   r   )r   ?q?kr.   Zqh?kh?weightsr    r    r!   rS   ?   s    
"&.
zMHAttentionMap.forward)r?   T)N)	rT   rU   rV   r?   r   r   r   rS   rW   r    r    )r   r!   r   ?   s   r   c             C   sX   | ? ? } | ?d?} d| | ?d? }| ?d?|?d? }d|d |d   }|?? | S )a?  
    Compute the DICE loss, similar to generalized IOU for masks
    Args:
        inputs: A float tensor of arbitrary shape.
                The predictions for each example.
        targets: A float tensor with the same shape as inputs. Stores the binary
                 classification label for each element in inputs
                (0 for the negative class and 1 for the positive class).
    r'   r*   r(   )rA   rZ   ?sum)?inputs?targets?	num_boxes?	numerator?denominator?lossr    r    r!   ?	dice_loss?   s    

r?   ?      ??r*   r.   )?alpha?gammac             C   s?   |dkst ?| ?? }tj| |dd?}|| d| d|   }|d| |  }	|dkrt|| d| d|   }
|
|	 }	|dkr?|	?d?}	|	?? | S )as  
    Loss used in RetinaNet for dense detection: https://arxiv.org/abs/1708.02002.
    Args:
        inputs: A float tensor of arbitrary shape.
                The predictions for each example.
        targets: A float tensor with the same shape as inputs. Stores the binary
                 classification label for each element in inputs
                (0 for the negative class and 1 for the positive class).
        num_boxes: num of prediction instance
        alpha: (optional) Weighting factor in range (0,1) to balance
                positive vs negative examples. Default = -1 (no weighting).
        gamma: Exponent of the modulating factor (1 - p_t) to
               balance easy vs hard examples.
        mode: a str, either "mask" or "box". When mode equal "mask", the loss would be averaged in
              the first dimension.
    Returns:
        Loss tensor
    )r.   ?box?none)?	reductionr'   r   r.   )r:   rA   r?   ? binary_cross_entropy_with_logits?meanr?   )r?   r?   r?   r?   r?   r~   ?prob?ce_loss?p_tr?   ?alpha_tr    r    r!   ?sigmoid_focal_loss?   s    
r?   c                   s.   e Zd Zd? fdd?	Ze?? dd? ?Z?  ZS )?PostProcessSegm?      ??c                s   t ? ??  || _d S )N)r   r   ?	threshold)r   r?   )r   r    r!   r   ?   s    
zPostProcessSegm.__init__c             C   s?   t |?t |?kst?|?d?d ?? \}}|d ?d?}tj|||fddd?}|?? | jk?	? }x?t
t|||??D ]x\}\}	}
}|
d |
d  }}|	d d ?d |?d |?f ?d?|| d< tj|| d ?? t|?? ?d	d
??? || d< qrW |S )Nr   r0   r*   ?bilinearF)r#   r~   ?align_cornersr'   ?masksr}   )r#   r~   )?lenr:   ?max?tolist?squeezer?   r   rA   r?   ?cpu?	enumerate?zipr6   r?   ?tuple?byte)r   ?results?outputs?orig_target_sizesZmax_target_sizesZmax_hZmax_wZoutputs_masks?iZcur_mask?t?tt?img_h?img_wr    r    r!   rS   ?   s     (0zPostProcessSegm.forward)r?   )rT   rU   rV   r   r3   ?no_gradrS   rW   r    r    )r   r!   r?   ?   s   r?   c                   s,   e Zd ZdZd? fdd?	Zd	dd?Z?  ZS )
?PostProcessPanopticz~This class converts the output of the model to the final panoptic result, in the format expected by the
    coco panoptic API ?      ??c                s   t ? ??  || _|| _dS )a?  
        Parameters:
           is_thing_map: This is a whose keys are the class ids, and the values a boolean indicating whether
                          the class is  a thing (True) or a stuff (False) class
           threshold: confidence threshold: segments with confidence lower than this will be deleted
        N)r   r   r?   ?is_thing_map)r   r?   r?   )r   r    r!   r     s    
zPostProcessPanoptic.__init__Nc          
      s?  |dkr|}t |?t |?ks t?|d |d |d   }}}t |?t |?  kr\t |?ksbn t?g }dd? ??xft|||||?D ?]P\}}	}
}?|?d??d?\}}|?|d jd d ?|| jk@ }|?d??d?\}}|| }|| }|	| }	t|	dd?df ?|?d	d
??	d?}	t
?|
| ?}
|	jdd? \??t |
?t |?k?sNt?|	?d?}	tdd? ??x8t|?D ],\}}| j|??  ?sn?|??  ?|? ?qnW d?????fdd?	}||	|dd?\? }|?? dk?rBx?tj? fdd?t|?D ?tj|jd?}|?? ?? ?r8||  }||  }|	|  }	||	|?\? }nP ?q?W ntjdtj|jd?}g }x<t? ?D ]0\}}|| ?? }|?|| j| ||d?? ?qdW ~t?? ?"}|j|dd? |?? |d?}W dQ R X |?|? q?W |S )a?   This function computes the panoptic prediction from the model's predictions.
        Parameters:
            outputs: This is a dict coming directly from the model. See the model doc for the content.
            processed_sizes: This is a list of tuples (or torch tensors) of sizes of the images that were passed to the
                             model, ie the size after data augmentation but before batching.
            target_sizes: This is a list of tuples (or torch tensors) corresponding to the requested final size
                          of each prediction. If left to None, it will default to the processed_sizes
            Nr+   r0   r,   c             S   s   t | t?r| S t| ?? ?? ?S )N)r1   r?   r?   r?   )?tupr    r    r!   ?to_tuple&  s    
z-PostProcessPanoptic.forward.<locals>.to_tupler(   r'   r?   )r~   r/   c               S   s   g S )Nr    r    r    r    r!   ?<lambda>>  s    z-PostProcessPanoptic.forward.<locals>.<lambda>Fc                s>  | ? dd??d?}|jd dkr:tj? ?ftj|jd?}n|?d??? ??}|r?x@??	? D ]4}t
|?dkrZx"|D ]}|?|?|?|d ? qpW qZW ???\}}t?t|?? ???? ?? ??}|j||ftjd?}t?tj?|?? ???||d??? }	t?t|	??}g }
x.tt
|??D ]}|
?|?|??? ?? ? ?qW |
|fS )Nr   r'   r(   )?dtype?device)r#   ?resamplera   )?	transposer?   r8   r3   ?zeros?longr?   ?argmaxrD   ?valuesr?   r?   ?eqr   ?	fromarrayr
   r?   ?numpy?resize?NEAREST?
ByteTensor?ByteStorage?from_buffer?tobytes?
from_numpyr   ?range?appendr?   ?item)r?   ?scores?dedupZm_id?equivZeq_idZfinal_hZfinal_w?seg_imgZ
np_seg_img?arear?   )?h?stuff_equiv_classes?target_sizer?   ?wr    r!   ?get_ids_areaC  s$    
$z1PostProcessPanoptic.forward.<locals>.get_ids_areaT)r?   r   c                s   g | ]\}}? | d k?qS )r]   r    )r$   r?   ?c)r?   r    r!   r&   j  s    z/PostProcessPanoptic.forward.<locals>.<listcomp>)r?   r?   )?id?isthing?category_idr?   ?PNG)?format)?
png_string?segments_info)F)r?   r:   r?   r?   r?   ?ner8   r?   r   r?   ?box_ops?box_cxcywh_to_xyxyrZ   r   r?   r?   r?   r?   ?numelr3   ?	as_tensor?boolr?   ?any?onesr?   ?io?BytesIO?save?getvalue)r   r?   Zprocessed_sizes?target_sizes?
out_logitsZ	raw_masksZ	raw_boxesZpredsZ
cur_logitsZ	cur_masksZ	cur_boxesr#   r?   ?labels?keepZ
cur_scoresZcur_classesr?   ?labelr?   r?   Zfiltered_smallr?   r?   rc   r   rQ   ?predictionsr    )r?   r?   r?   r?   r?   r?   r!   rS     s^    	&"$
""



 
zPostProcessPanoptic.forward)r?   )N)rT   rU   rV   r?   r   rS   rW   r    r    )r   r!   r?     s   r?   )r?   r*   r.   )%r?   r?   ?collectionsr   ?typingr   r   r3   ?torch.nnrd   ?torch.nn.functional?
functionalr?   r   ?PILr   ?util.box_opsr?   ?	util.miscr   r   r	   ?panopticapi.utilsr
   r   ?ImportError?Moduler   rY   r\   r   r   r?   r?   r?   r?   r?   r    r    r    r!   ?<module>   s,   7G $