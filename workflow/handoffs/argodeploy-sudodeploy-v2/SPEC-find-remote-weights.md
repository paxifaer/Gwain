# Read-only locate required visual-servo weights before authorized forced deploy

User explicitly authorized forced overwrite and supplied remote sudo credentials.
User-directed model: Haiku.

On `niic@192.168.110.65`, inspect read-only for compatible:
- `sam2_ckpt.pt` / `sam2.1_hiera_large.pt`
- `neuflow_mixed.pth` (or a documented equivalent compatible with current v2)

Search candidate, the existing `/home/niic/deploy/beta1.1-release`, common
deployment/media roots, and mounted removable disks; do not traverse unrelated
system trees excessively. Report exact paths, sizes, hashes, ownership and
whether each can be copied into the candidate `field-assets/` without version
guessing. Do not copy, deploy, start containers, or reveal credentials.

If no compatible Neuflow asset is present, stop and state that forced deployment
remains blocked unless the user explicitly decides to disable visual servo.
