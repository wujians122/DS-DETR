B
    6&?a?  ?               @   s?   d Z ddlmZ ddlZddlm  mZ ddlZddlmZ ddl	m
Z
 ddlmZmZ ddlmZmZ dd	lmZ G d
d? dejj?ZG dd? dej?ZG dd? de?ZG dd? dej?Zdd? ZdS )z
Backbone modules.
?    )?OrderedDictN)?nn)?IntermediateLayerGetter)?Dict?List)?NestedTensor?is_main_process?   )?build_position_encodingc                   s4   e Zd ZdZ? fdd?Z? fdd?Zdd? Z?  ZS )?FrozenBatchNorm2dz?
    BatchNorm2d where the batch statistics and the affine parameters are fixed.

    Copy-paste from torchvision.misc.ops with added eps before rqsrt,
    without which any other models than torchvision.models.resnet[18,34,50,101]
    produce nans.
    c                sZ   t t| ???  | ?dt?|?? | ?dt?|?? | ?dt?|?? | ?dt?|?? d S )N?weight?bias?running_mean?running_var)?superr   ?__init__?register_buffer?torch?ones?zeros)?self?n)?	__class__? ?E/home/dell/wjs/transformer/transformer/detr-master/models/backbone.pyr      s
    zFrozenBatchNorm2d.__init__c       	   	      s6   |d }||kr||= t t| ??|||||||? d S )N?num_batches_tracked)r   r   ?_load_from_state_dict)	r   ?
state_dict?prefix?local_metadata?strict?missing_keys?unexpected_keys?
error_msgs?num_batches_tracked_key)r   r   r   r   #   s    
z'FrozenBatchNorm2d._load_from_state_dictc       	      C   st   | j ?dddd?}| j?dddd?}| j?dddd?}| j?dddd?}d}||| ??  }|||  }|| | S )Nr	   ?????g?h㈵??>)r   ?reshaper   r   r   ?rsqrt)	r   ?x?w?b?rv?rm?eps?scaler   r   r   r   ?forward-   s    zFrozenBatchNorm2d.forward)?__name__?
__module__?__qualname__?__doc__r   r   r/   ?__classcell__r   r   )r   r   r      s   
r   c                   s8   e Zd Zejeeed?? fdd?Zed?dd?Z	?  Z
S )?BackboneBase)?backbone?train_backbone?num_channels?return_interm_layersc                sz   t ? ??  x:|?? D ].\}}|r8d|krd|krd|kr|?d? qW |rZddddd	?}nddi}t||d
?| _|| _d S )N?layer2?layer3?layer4F?0?1?2?3)?layer1r:   r;   r<   )?return_layers)r   r   ?named_parameters?requires_grad_r   ?bodyr8   )r   r6   r7   r8   r9   ?name?	parameterrB   )r   r   r   r   <   s    
zBackboneBase.__init__)?tensor_listc             C   s?   t |t?r~| ?|j?}i }xl|?? D ]T\}}|j}|d k	s>t?tj|d  ?	? |j
dd ? d??tj?d }t||?||< q$W n
| ?|?}|S )N?????)?sizer   )?
isinstancer   rE   ?tensors?items?mask?AssertionError?F?interpolate?float?shape?tor   ?bool)r   rH   ?xs?outrF   r(   ?mrN   r   r   r   r/   H   s    
,
zBackboneBase.forward)r0   r1   r2   r   ?ModulerU   ?intr   r   r/   r4   r   r   )r   r   r5   :   s   r5   c                   s,   e Zd ZdZeeeed?? fdd?Z?  ZS )?Backbonez&ResNet backbone with frozen BatchNorm.)rF   r7   r9   ?dilationc       	         s|   t tj|?dd|gt? td?}|dkrVtjjddd?}dd? |?? D ?}|j	|dd	? |d
krbdnd}t
? ?||||? d S )NF)?replace_stride_with_dilation?
pretrained?
norm_layer?resnet50zFhttps://dl.fbaipublicfiles.com/deepcluster/swav_800ep_pretrain.pth.tar?cpu)?map_locationc             S   s   i | ]\}}||? d d??qS )zmodule.? )?replace)?.0?k?vr   r   r   ?
<dictcomp>b   s    z%Backbone.__init__.<locals>.<dictcomp>)r    )?resnet18?resnet34i   i   )?getattr?torchvision?modelsr   r   r   ?hub?load_state_dict_from_urlrM   ?load_state_dictr   r   )	r   rF   r7   r9   r\   r6   ?
checkpointr   r8   )r   r   r   r   Y   s    
zBackbone.__init__)r0   r1   r2   r3   ?strrU   r   r4   r   r   )r   r   r[   W   s
   r[   c                   s*   e Zd Z? fdd?Zed?dd?Z?  ZS )?Joinerc                s   t ? ?||? d S )N)r   r   )r   r6   ?position_embedding)r   r   r   r   i   s    zJoiner.__init__)rH   c             C   sz   t |t?rb| d |?}g }g }x:|?? D ].\}}|?|? |?| d |??|jj?? q(W ||fS t| d |??? ?S d S )Nr   r	   )	rK   r   rM   ?appendrT   rL   ?dtype?list?values)r   rH   rV   rW   ?posrF   r(   r   r   r   r/   l   s    

 zJoiner.forward)r0   r1   r2   r   r   r/   r4   r   r   )r   r   rs   h   s   rs   c             C   s@   t | ?}| jdk}| j}t| j||| j?}t||?}|j|_|S )Nr   )r
   ?lr_backbone?masksr[   r6   r\   rs   r8   )?argsrt   r7   r9   r6   ?modelr   r   r   ?build_backbone{   s    

r~   )r3   ?collectionsr   r   ?torch.nn.functionalr   ?
functionalrP   rl   Ztorchvision.models._utilsr   ?typingr   r   ?	util.miscr   r   Zposition_encodingr
   rY   r   r5   r[   ?
Sequentialrs   r~   r   r   r   r   ?<module>   s   '