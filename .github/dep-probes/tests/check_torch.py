"""Compatibility probe for torch (CPU build).

The candidate declares the pytorch-cpu index, so the build under test must
be the CPU wheel: a CUDA build here means the index pin failed and the
image would grow by the whole nvidia-* dependency set. The meaningful
checks are the build discriminator (torch.version.cuda is None on CPU
wheels), seeded tensor ops, and a tiny autograd training loop - all on
synthetic data, no filesystem or network access.
"""

import torch


def main() -> None:
    # Build discriminator: CPU wheels report no CUDA runtime. The probe
    # runner has no GPU either way, so torch.cuda.is_available() alone
    # cannot tell the variants apart; torch.version.cuda is the reliable
    # signal (a CUDA build reports e.g. "13.x", a CPU build None).
    assert torch.version.cuda is None, f"expected CPU build, got CUDA {torch.version.cuda}"
    assert not torch.cuda.is_available(), "CUDA device visible on the CPU-only image"

    # Core tensor ops on synthetic, seeded data.
    torch.manual_seed(42)
    a = torch.randn(4, 3)
    b = torch.randn(3, 2)
    c = a @ b
    assert c.shape == (4, 2), f"matmul shape = {tuple(c.shape)}"
    assert bool(torch.isfinite(c).all()), "matmul produced non-finite values"

    # Autograd round-trip: a tiny linear regression trained to convergence
    # on seeded synthetic data exercises nn.Module, the optimizer, and the
    # backward pass end to end.
    torch.manual_seed(7)
    model = torch.nn.Linear(1, 1)
    x = torch.linspace(-1.0, 1.0, 16).unsqueeze(1)
    y = 3.0 * x + 1.0
    optimizer = torch.optim.SGD(model.parameters(), lr=0.1)
    for _ in range(200):
        optimizer.zero_grad()
        loss = torch.nn.functional.mse_loss(model(x), y)
        loss.backward()
        optimizer.step()
    weight = model.weight.item()
    bias = model.bias.item()
    assert abs(weight - 3.0) < 0.2, f"weight = {weight}"
    assert abs(bias - 1.0) < 0.2, f"bias = {bias}"
    print("torch: OK (CPU build, tensor ops + autograd round-trip)")


if __name__ == "__main__":
    main()
