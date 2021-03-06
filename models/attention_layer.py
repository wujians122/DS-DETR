B
    ܄ha?J  ?               @   s?   d dl Z d dlmZmZ d dl mZ d dlmZ d dlmZm	Z	m
Z
 d dlZdeeeeeeeee ee eeeeeee eee eee ee ee ee ee ee e	eee f d?d	d
?ZG dd? de?ZdS )?    N)?linear?pad)?Tensor)?MultiheadAttention)?Optional?Tuple?ListTF)?query?key?value?embed_dim_to_check?	num_heads?in_proj_weight?in_proj_bias?bias_k?bias_v?add_zero_attn?	dropout_p?out_proj_weight?out_proj_bias?training?key_padding_mask?need_weights?	attn_mask?use_separate_proj_weight?q_proj_weight?k_proj_weight?v_proj_weight?static_k?static_v?gaussian?returnc       -      C   s?  | ? ? \}}}||kst?|? d?|? d?krB|? d?|? d?ksFt?|| }|| |ksbtd??t|?d }|?s@t?| |?r?t?||?r?t| ||?jddd?\}}}?qVt?||??rn|} d}!|}"||!|"?dd?f }#| dk	r?| |!|"? } t| |#| ?}|dk?r|dk?st?d}d}nP|} |}!d}"||!d?dd?f }#| dk	?rR| |!d? } t||#| ?jd	dd?\}}n?|} d}!|}"||!|"?dd?f }#| dk	?r?| |!|"? } t| |#| ?}|} |}!|d	 }"||!|"?dd?f }#| dk	?r?| |!|"? } t||#| ?}|} |d	 }!d}"||!d?dd?f }#| dk	?r0| |!d? } t||#| ?}?ntj?|?}$|$? ? \}%}&|%|k?rr|&| ? d?k?svt?tj?|?}'|'? ? \}%}&|%|k?r?|&|? d?k?s?t?tj?|?}(|(? ? \}%}&|%|k?r?|&|? d?k?s?t?|dk	?r2t| |$|d|? ?}t||'|||d	 ? ?}t||(||d	 d? ?}n$t| |$|?}t||'|?}t||(|?}|| }|dk	?rz|j	tj
k?s?|j	tjk?s?|j	tjk?s?|j	tjk?s?|j	tjk?s?td
?|j	???|j	tjk?r?t?d? |?tj?}|?? d	k?r(|?d?}t|? ? ?d| ? d?|? d?gk?rztd??nR|?? dk?rht|? ? ?|| | ? d?|? d?gk?rztd??ntd?|?? ???|dk	?r?|j	tjk?r?t?d? |?tj?}|dk	?rP|dk	?rP|dk?r*|dk?r*t?||?d|d?g?}t?||?d|d?g?}|dk	?rt|d?}|dk	?rNt|d?}n$|dk?s<td??|dk?sltd??n|dk?s^t?|dk?slt?|?? ?||| |??dd?}|dk	?r?|?? ?d|| |??dd?}|dk	?r?|?? ?d|| |??dd?}|dk	?r|? d?|| k?s?t?|? d	?|k?st?|}|dk	?rN|? d?|| k?s6t?|? d	?|k?sJt?|}|? d?})|dk	?r?|? d?|k?svt?|? d?|)k?s?t?|	?r8|)d7 })tj|tj|? d?df|? ? d	d?  |j	|jd?gdd?}tj|tj|? d?df|? ? d	d?  |j	|jd?gdd?}|dk	?r$t|d?}|dk	?r8t|d?}d}*|*?rXt?||?dd	??}+t|+? ? ?|| ||)gk?svt?|dk	?r?|j	tjk?r?|+? |td?? n|+|7 }+|dk	?r?|+?||||)?}+|+?!|?d??d	?td??}+|+?|| ||)?}+|+|d ?"d	dd? }+tj#j$j%|+dd?}+tj#j$j&|+|
|d?}+t?|+|?},t|,? ? ?|| ||gk?sXt?|,?dd??? ?|||?},t|,||?},|,|+?||||)?fS )ag  
    Args:
        query, key, value: map a query and a set of key-value pairs to an output.
            See "Attention Is All You Need" for more details.
        embed_dim_to_check: total dimension of the model.
        num_heads: parallel attention heads.
        in_proj_weight, in_proj_bias: input projection weight and bias.
        bias_k, bias_v: bias of the key and value sequences to be added at dim=0.
        add_zero_attn: add a new batch of zeros to the key and
                       value sequences at dim=1.
        dropout_p: probability of an element to be zeroed.
        out_proj_weight, out_proj_bias: the output projection weight and bias.
        training: apply dropout if is ``True``.
        key_padding_mask: if provided, specified padding elements in the key will
            be ignored by the attention. This is an binary mask. When the value is True,
            the corresponding value on the attention layer will be filled with -inf.
        need_weights: output attn_output_weights.
        attn_mask: 2D or 3D mask that prevents attention to certain positions. A 2D mask will be broadcasted for all
            the batches while a 3D mask allows to specify a different mask for the entries of each batch.
        use_separate_proj_weight: the function accept the proj. weights for query, key,
            and value in different forms. If false, in_proj_weight will be used, which is
            a combination of q_proj_weight, k_proj_weight, v_proj_weight.
        q_proj_weight, k_proj_weight, v_proj_weight: input projection weight and bias.
        static_k, static_v: static key and value used for attention operators.
        gaussian: the generated Gaussian-like weight map
    Shape:
        Inputs:
        - query: :math:`(L, N, E)` where L is the target sequence length, N is the batch size, E is
          the embedding dimension.
        - key: :math:`(S, N, E)`, where S is the source sequence length, N is the batch size, E is
          the embedding dimension.
        - value: :math:`(S, N, E)` where S is the source sequence length, N is the batch size, E is
          the embedding dimension.
        - key_padding_mask: :math:`(N, S)` where N is the batch size, S is the source sequence length.
          If a ByteTensor is provided, the non-zero positions will be ignored while the zero positions
          will be unchanged. If a BoolTensor is provided, the positions with the
          value of ``True`` will be ignored while the position with the value of ``False`` will be unchanged.
        - attn_mask: 2D mask :math:`(L, S)` where L is the target sequence length, S is the source sequence length.
          3D mask :math:`(N*num_heads, L, S)` where N is the batch size, L is the target sequence length,
          S is the source sequence length. attn_mask ensures that position i is allowed to attend the unmasked
          positions. If a ByteTensor is provided, the non-zero positions are not allowed to attend
          while the zero positions will be unchanged. If a BoolTensor is provided, positions with ``True``
          are not allowed to attend while ``False`` values will be unchanged. If a FloatTensor
          is provided, it will be added to the attention weight.
        - static_k: :math:`(N*num_heads, S, E/num_heads)`, where S is the source sequence length,
          N is the batch size, E is the embedding dimension. E/num_heads is the head dimension.
        - static_v: :math:`(N*num_heads, S, E/num_heads)`, where S is the source sequence length,
          N is the batch size, E is the embedding dimension. E/num_heads is the head dimension.
        Outputs:
        - attn_output: :math:`(L, N, E)` where L is the target sequence length, N is the batch size,
          E is the embedding dimension.
        - attn_output_weights: :math:`(N, L, S)` where N is the batch size,
          L is the target sequence length, S is the source sequence length.
    r   ?   z(embed_dim must be divisible by num_headsg      ???   ?????)?dimN?   zDOnly float, byte, and bool types are supported for attn_mask, not {}zZByte tensor for attn_mask in nn.MultiheadAttention is deprecated. Use bool tensor instead.z,The size of the 2D attn_mask is not correct.z,The size of the 3D attn_mask is not correct.z)attn_mask's dimension {} is not supportedzaByte tensor for key_padding_mask in nn.MultiheadAttention is deprecated. Use bool tensor instead.)r   r"   z#bias cannot be added to static key.z%bias cannot be added to static value.)?dtype?deviceTz-inf)?pr   )'?size?AssertionError?float?torch?equalr   ?chunk?jit?_unwrap_optionalr'   ?float32?float64?float16?uint8?bool?format?warnings?warn?tor%   ?	unsqueeze?list?RuntimeError?cat?repeatr   ?
contiguous?view?	transpose?zerosr(   ?bmm?masked_fill_?masked_fill?permute?nn?
functional?softmax?dropout)-r	   r
   r   r   r   r   r   r   r   r   r   r   r   r   r   r   r   r   r   r   r   r   r   r    ?tgt_len?bsz?	embed_dim?head_dim?scaling?q?k?v?_b?_start?_end?_wZq_proj_weight_non_opt?len1?len2Zk_proj_weight_non_optZv_proj_weight_non_opt?src_len?naive?attn_output_weights?attn_output? r^   ?L/home/dell/wjs/transformer/transformer/detr-master/models/attention_layer.py?multi_head_attention_forward
   s   P, 






,

$
(










<<



 

 r`   c                   s&   e Zd Z? fdd?Zddd?Z?  ZS )?GaussianMultiheadAttentionc                s    t t| ?j||f|? d| _d S )NT)?superra   ?__init__r    )?selfrN   r   ?kwargs)?	__class__r^   r_   rc     s    z#GaussianMultiheadAttention.__init__NFc             C   s?   | j sZt|||| j| j| j| j| j| j| j| j	| j
j| j
j| j|||d| j| j| j|d?S t|||| j| j| j| j| j| j| j| j	| j
j| j
j| j||||d?S dS )a?  
    Args:
        query, key, value: map a query and a set of key-value pairs to an output.
            See "Attention Is All You Need" for more details.
        key_padding_mask: if provided, specified padding elements in the key will
            be ignored by the attention. When given a binary mask and a value is True,
            the corresponding value on the attention layer will be ignored. When given
            a byte mask and a value is non-zero, the corresponding value on the attention
            layer will be ignored
        need_weights: output attn_output_weights.
        attn_mask: 2D or 3D mask that prevents attention to certain positions. A 2D mask will be broadcasted for all
            the batches while a 3D mask allows to specify a different mask for the entries of each batch.
        gaussian: 2D gaussian attention map that focus attention to certain object queries' initial estimations
            with handcrafted query spatial priors.

    Shape:
        - Inputs:
        - query: :math:`(L, N, E)` where L is the target sequence length, N is the batch size, E is
          the embedding dimension.
        - key: :math:`(S, N, E)`, where S is the source sequence length, N is the batch size, E is
          the embedding dimension.
        - value: :math:`(S, N, E)` where S is the source sequence length, N is the batch size, E is
          the embedding dimension.
        - key_padding_mask: :math:`(N, S)` where N is the batch size, S is the source sequence length.
          If a ByteTensor is provided, the non-zero positions will be ignored while the position
          with the zero positions will be unchanged. If a BoolTensor is provided, the positions with the
          value of ``True`` will be ignored while the position with the value of ``False`` will be unchanged.
        - attn_mask: 2D mask :math:`(L, S)` where L is the target sequence length, S is the source sequence length.
          3D mask :math:`(N*num_heads, L, S)` where N is the batch size, L is the target sequence length,
          S is the source sequence length. attn_mask ensure that position i is allowed to attend the unmasked
          positions. If a ByteTensor is provided, the non-zero positions are not allowed to attend
          while the zero positions will be unchanged. If a BoolTensor is provided, positions with ``True``
          is not allowed to attend while ``False`` values will be unchanged. If a FloatTensor
          is provided, it will be added to the attention weight.
        - gaussian: :math:`(L, S, nhead * batch_size)`, where nhead is the number of head in multi-head
          attention module, L is the target sequence length, S is the source sequence length.

        - Outputs:
        - attn_output: :math:`(L, N, E)` where L is the target sequence length, N is the batch size,
          E is the embedding dimension.
        - attn_output_weights: :math:`(N, L, S)` where N is the batch size,
          L is the target sequence length, S is the source sequence length.
        T)	r   r   r   r   r   r   r   r   r    )r   r   r   r   r    N)?_qkv_same_embed_dimr`   rN   r   r   r   r   r   r   rK   ?out_proj?weight?biasr   r   r   r   )rd   r	   r
   r   r   r   r   r    r^   r^   r_   ?forward  s&    .z"GaussianMultiheadAttention.forward)NFNN)?__name__?
__module__?__qualname__rc   rk   ?__classcell__r^   r^   )rf   r_   ra     s    ra   )TNTNFNNNNNN)r-   ?torch.nn.functionalr   r   r   ?torch.nnr   ?typingr   r   r   r8   ?intr6   r,   r`   ra   r^   r^   r^   r_   ?<module>   s&             Z t