B
    `Q?aAG  ?               @   s?   d Z ddlZddlmZmZ ddlZddlm  mZ	 ddlmZm
Z
 ddlmZ ddlmZmZ dZG d	d
? d
ej?ZG dd? dej?ZG dd? dej?ZG dd? dej?ZG dd? dej?Zdd? Zdd? ZG dd? dej?Zdd? ZdS )z?
DETR Transformer class.

Copy-paste from torch.nn.Transformer with modifications:
    * positional encodings are passed in MHattention
    * extra LN at the end of encoder is removed
    * decoder returns a stack of activations from all decoding layers
?    N)?Optional?List)?nn?Tensor?   )?GaussianMultiheadAttention)?RPEMultiheadAttention?irpeaM  
we can use a string to represent a kind of 2D-RPE
Format:
  rpe-{ratio}-{method}-{mode}-{shared_head}-{rpe_on}
e.g. rpe-2.0-product-ctx-1-k
it represents
    ratio=2.0,
    method='product',
    mode='ctx',
    shared_head=True,
    rpe_on='k',

ratio | num_buckets
------|------------
1.9   | 49
2.0   | 81
2.5   | 121
3.0   | 169
c                   s.   e Zd Zd? fd
d?	Zdd? Zdd? Z?  ZS )?Transformer?   ?   ?   ?   皙???????reluFT? c                s?  t ? ??  |d kst|?dkr$d }n?y?|?d?}t|?dksHtt|???|d dksXt?t|d ?}|d }|d }tt|d ??}|d	 }tj	||||d|d
?}W n   t
dt ? ? Y nX t|||||||d?}|r?t?|?nd }t|||?| _g }x4t|?D ](}t||
|||||||?	}|?|? ?qW t?|?}t||||	d?| _| ??  |dk?r?xVt|?D ]J}tj?| jj| jj? t?? ? tj?| jj| jj? W d Q R X ?qhW || _ || _!d S )Nr   ?-r   Zrper   ?   ?   ?   ?   )?ratio?method?mode?shared_head?skip?rpe_onzWrong Format:)?
rpe_config)?return_intermediate)?type2?type3?type4)"?super?__init__?len?split?AssertionError?float?bool?intr	   Zget_rpe_config?print?RPE_HELP?TransformerEncoderLayerr   ?	LayerNorm?TransformerEncoder?encoder?range?TransformerDecoderLayer?append?TransformerDecoder?decoder?_reset_parameters?init?zeros_?layers?point3?weight?torch?no_grad?ones_?bias?d_model?nhead)?selfr?   r@   ?num_encoder_layers?num_decoder_layers?dim_feedforward?dropout?
activation?normalize_before?return_intermediate_dec?smooth?dynamic_scale?	enc_rpe2dr   ?spr   r   r   r   r   ?encoder_layer?encoder_normZdecoder_layers?layer_index?decoder_layer?decoder_norm)?	__class__? ?H/home/dell/wjs/transformer/transformer/detr-master/models/transformer.pyr#   (   sX    





(zTransformer.__init__c             C   s.   x(| ? ? D ]}|?? dkr
tj?|? q
W d S )Nr   )?
parameters?dimr   r6   ?xavier_uniform_)rA   ?prS   rS   rT   r5   b   s    zTransformer._reset_parametersc          	   C   s  |j \}}}}	t?t?d|?t?d|	??\}
}t?||
fd??? ?|j?}|?dd??	d??
d|d d?}|?d??ddd?}|?d??ddd?}|?	d??
d|d?}|?d?}t?|?}| j|||||	fd?}| j|||||||d?\}}|?dd?|?dd?|?ddd??||||	?fS )Nr   r   ?????r   r   )?src_key_padding_mask?pos?hw)?memory_key_padding_maskr[   ?	query_pos)?shaper;   ?meshgrid?arange?stackr'   ?to?device?reshape?	unsqueeze?repeat?flatten?permute?
zeros_liker/   r4   ?	transpose?view)rA   ?src?mask?query_embedZ	pos_embed?h_w?bs?c?h?wZgrid_yZgrid_x?grid?tgt?memory?hs?pointsrS   rS   rT   ?forwardg   s      

zTransformer.forward)r   r   r   r   r   r   r   FFr   Tr   )?__name__?
__module__?__qualname__r#   r5   rz   ?__classcell__rS   rS   )rR   rT   r
   &   s      7r
   c                   s>   e Zd Zd? fdd?	Zdee ee ee d?dd?Z?  ZS )	r.   Nc                s&   t ? ??  t||?| _|| _|| _d S )N)r"   r#   ?_get_clonesr8   ?
num_layers?norm)rA   rM   r?   r?   )rR   rS   rT   r#   ?   s    
zTransformerEncoder.__init__)rn   rZ   r[   c             C   s>   |}x | j D ]}||||||d?}qW | jd k	r:| ?|?}|S )N)?src_maskrZ   r[   r\   )r8   r?   )rA   rm   rn   rZ   r[   r\   ?output?layerrS   rS   rT   rz   ?   s    

zTransformerEncoder.forward)N)NNNN)r{   r|   r}   r#   r   r   rz   r~   rS   rS   )rR   rT   r.   ~   s     r.   c                   sP   e Zd Zd? fdd?	Zd	ee ee ee ee ee ee d?dd?Z?  ZS )
r3   NFc                s,   t ? ??  t?|?| _|| _|| _|| _d S )N)r"   r#   r   ?
ModuleListr8   r?   r?   r   )rA   rP   r?   r?   r   )rR   rS   rT   r#   ?   s
    
zTransformerDecoder.__init__)?tgt_mask?memory_mask?tgt_key_padding_maskr]   r[   r^   c             C   s?   |}g }g }d }xR| j D ]H}||||||||||	|
|d?\}}}|?|? | jr|?| ?|?? qW | jd k	r?| ?|?}| jr?|??  |?|? | jr?t?|?|d fS |?d?S )N)r?   r?   r?   r]   r[   r^   ?point_ref_previousr   )r8   r2   r   r?   ?popr;   rb   rf   )rA   ru   rp   rv   rw   r?   r?   r?   r]   r[   r^   r?   Zintermediatery   ?point_sigmoid_refr?   ?pointrS   rS   rT   rz   ?   s,    




zTransformerDecoder.forward)NF)NNNNNN)r{   r|   r}   r#   r   r   rz   r~   rS   rS   )rR   rT   r3   ?   s        r3   c                   s?   e Zd Zd? fdd?	Zee d?d	d
?Zdee ee ee d?dd?Zdee ee ee d?dd?Zdee ee ee d?dd?Z	?  Z
S )r,   ?   皙??????r   FNc                s?   t ? ??  t||||d?| _t?||?| _t?|?| _t?||?| _	t?
|?| _t?
|?| _t?|?| _t?|?| _t|?| _|| _d S )N)rE   r   )r"   r#   r   ?	self_attnr   ?Linear?linear1?DropoutrE   ?linear2r-   ?norm1?norm2?dropout1?dropout2?_get_activation_fnrF   rG   )rA   r?   r@   rD   rE   rF   rG   r   )rR   rS   rT   r#   ?   s    

z TransformerEncoderLayer.__init__)r[   c             C   s   |d kr|S || S )NrS   )rA   ?tensorr[   rS   rS   rT   ?with_pos_embed?   s    z&TransformerEncoderLayer.with_pos_embed)r?   rZ   r[   c       	   	   C   sz   | ? ||? }}| j||||||d?d }|| ?|? }| ?|?}| ?| ?| ?| ?|????}|| ?|? }| ?	|?}|S )N)?value?	attn_mask?key_padding_maskr\   r   )
r?   r?   r?   r?   r?   rE   rF   r?   r?   r?   )	rA   rm   r?   rZ   r[   r\   ?q?k?src2rS   rS   rT   ?forward_post?   s    

z$TransformerEncoderLayer.forward_postc       	   	   C   sx   | ? |?}| ?||? }}| j|||||d?d }|| ?|? }| ?|?}| ?| ?| ?| ?|????}|| ?	|? }|S )N)r?   r?   r?   r   )
r?   r?   r?   r?   r?   r?   rE   rF   r?   r?   )	rA   rm   r?   rZ   r[   r\   r?   r?   r?   rS   rS   rT   ?forward_pre?   s    

z#TransformerEncoderLayer.forward_prec             C   s.   | j r| j|||||d?S | j|||||d?S )N)r\   )rG   r?   r?   )rA   rm   r?   rZ   r[   r\   rS   rS   rT   rz   ?   s    zTransformerEncoderLayer.forward)r?   r?   r   FN)NNNN)NNNN)NNNN)r{   r|   r}   r#   r   r   r?   r?   r?   rz   r~   rS   rS   )rR   rT   r,   ?   s            r,   c            	       s?   e Zd Zd? fdd?	Zee d?dd	?Zdee ee ee ee ee ee ee d?dd?Zdee ee ee ee ee ee d?dd?Zdee ee ee ee ee ee ee d?dd?Z	?  Z
S )r1   ?   皙??????r   Fc
       
         sV  t ? ??  tj|||d?| _t|||d?| _t?||?| _t?	|?| _
t?||?| _|| _|| _t?|?| _t?|?| _t?|?| _t?|?| _t?	|?| _t?	|?| _t?	|?| _|dkr?tdddd?| _t?|d?| _nt?|d?| _|| _| jdk?rt?|d?| _n6| jd	k?r(t?|d?| _n| jd
k?rBt?|d?| _t|?| _|	| _d S )N)rE   r   ?   r   r   ?   r   r   r    r!   ?   )r"   r#   r   ?MultiheadAttentionr?   r   ?multihead_attnr?   r?   r?   rE   r?   rI   rJ   r-   r?   r?   ?norm3?norm4r?   r?   ?dropout3?MLP?point1?point2rO   r9   r?   rF   rG   )
rA   rJ   rI   rO   r?   r@   rD   rE   rF   rG   )rR   rS   rT   r#     s8    

z TransformerDecoderLayer.__init__)r[   c             C   s   |d kr|S || S )NrS   )rA   r?   r[   rS   rS   rT   r?   *  s    z&TransformerDecoderLayer.with_pos_embedN)r?   r?   r?   r]   r[   r^   r?   c          	   C   s?  |j d }| ?||
 ?}| ?|?}| ?||
? }}| j|||||d?d }|| ?|? }| ?|?}| jdkr?| ?|?}|?	? }|d | d }|?
ddd?}n|}|| }|?|dd?}|?d?|?d? ?d?}| jdkr?d}|?d?| }n?| jd	k?r0| ?|?}|| }|?|d??d?}|?d?| }n?| jd
k?rr| ?|?}|| }|?|dd??d?}|| ?d?}n^| jdk?r?| ?|?}|| }|?|dd??d?}tj|tj|ddd?gdd?}|| ?d?}|d ??  | j }| j| ?||
?| ?||	?||||gd?d }|| ?|? }| ?|?}| ?| ?| ?| ?|????}|| ?|? }| ?|?}| jdk?rr|||fS |d |fS d S )Nr   )r?   r?   r?   ?    r   r   rY   r   ?type1r   r    r!   r   T)rV   ?keepdim)rV   )?query?keyr?   r?   r?   ?gaussian) r_   r?   r?   r?   r?   r?   r?   rO   r?   ?sigmoidrg   rl   rf   ?powrJ   ?sumr9   re   r;   ?cat?prod?absrI   r?   r?   r?   r?   rE   rF   r?   r?   r?   )rA   ru   rp   rv   rw   r?   r?   r?   r]   r[   r^   r?   ?tgt_len?outZpoint_sigmoid_offsetr?   r?   ?tgt2Zpoint_sigmoid_ref_interr?   r?   ?distance?scaler?   rS   rS   rT   r?   -  sd    












z$TransformerDecoderLayer.forward_post)r?   r?   r?   r]   r[   r^   c	          	   C   s?   | ? |?}	| ?|	|? }
}| j|
||	||d?d }	|| ?|	? }| ?|?}	| j| ?|	|?| ?||?|||d?d }	|| ?|	? }| ?|?}	| ?| ?	| ?
| ?|	????}	|| ?|	? }|S )N)r?   r?   r?   r   )r?   r?   r?   r?   r?   )r?   r?   r?   r?   r?   r?   r?   r?   r?   rE   rF   r?   r?   )rA   rv   rw   r?   r?   r?   r]   r[   r^   r?   r?   r?   rS   rS   rT   r?   n  s    



z#TransformerDecoderLayer.forward_prec             C   s<   | j r| ?|||||||	|
?S | ?|||||||||	|
|?S )N)rG   r?   r?   )rA   ru   rp   rv   rw   r?   r?   r?   r]   r[   r^   r?   rS   rS   rT   rz   ?  s    zTransformerDecoderLayer.forward)r?   r?   r   F)NNNNNNN)NNNNNN)NNNNNNN)r{   r|   r}   r#   r   r   r?   r?   r?   rz   r~   rS   rS   )rR   rT   r1     s.    %      8;     2      r1   c                s   t ?? fdd?t|?D ??S )Nc                s   g | ]}t ?? ??qS rS   )?copy?deepcopy)?.0?i)?modulerS   rT   ?
<listcomp>?  s    z_get_clones.<locals>.<listcomp>)r   r?   r0   )r?   ?NrS   )r?   rT   r   ?  s    r   c             C   s2   t | j| j| j| j| j| j| jd| j| j	| j
d?S )NT)r?   rE   r@   rD   rB   rC   rG   rH   rI   rJ   rK   )r
   ?
hidden_dimrE   ?nheadsrD   Z
enc_layers?
dec_layersZpre_normrI   rJ   rK   )?argsrS   rS   rT   ?build_transformer?  s    r?   c                   s(   e Zd ZdZ? fdd?Zdd? Z?  ZS )r?   z5 Very simple multi-layer perceptron (also called FFN)c                sJ   t ? ??  || _|g|d  }t?dd? t|g| ||g ?D ??| _d S )Nr   c             s   s   | ]\}}t ?||?V  qd S )N)r   r?   )r?   ?nr?   rS   rS   rT   ?	<genexpr>?  s    zMLP.__init__.<locals>.<genexpr>)r"   r#   r?   r   r?   ?zipr8   )rA   ?	input_dimr?   ?
output_dimr?   rs   )rR   rS   rT   r#   ?  s    
zMLP.__init__c             C   s@   x:t | j?D ],\}}|| jd k r0t?||??n||?}qW |S )Nr   )?	enumerater8   r?   ?Fr   )rA   ?xr?   r?   rS   rS   rT   rz   ?  s    (zMLP.forward)r{   r|   r}   ?__doc__r#   rz   r~   rS   rS   )rR   rT   r?   ?  s   r?   c             C   s>   | dkrt jS | dkrt jS | dkr*t jS td| ? d???dS )z,Return an activation function given a stringr   ?gelu?gluz$activation should be relu/gelu, not ?.N)r?   r   r?   r?   ?RuntimeError)rF   rS   rS   rT   r?   ?  s    r?   )r?   r?   ?typingr   r   r;   ?torch.nn.functionalr   ?
functionalr?   r   Zattention_layerr   Zrpe_attentionr   r	   r+   ?Moduler
   r.   r3   r,   r1   r   r?   r?   r?   rS   rS   rS   rT   ?<module>	   s$   X.= 