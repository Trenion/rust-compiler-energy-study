use std::f64;

fn mandelbrot(c_re: f64, c_im: f64, max_iter: u32) -> u32 {
    let mut x = 0.0f64;
    let mut y = 0.0f64;
    let mut iter = 0;
    while x*x + y*y <= 4.0 && iter < max_iter {
        let x_new = x*x - y*y + c_re;
        y = 2.0*x*y + c_im;
        x = x_new;
        iter += 1;
    }
    iter
}

fn main() {
    let width: usize = 4000;
    let height: usize = 4000;
    let max_iter: u32 = 1000;
    let mut output = 0u64; // Dummy aggregation to prevent optimization

    for y in 0..height {
        let c_im = (y as f64 / height as f64) * 3.0 - 1.5;
        for x in 0..width {
            let c_re = (x as f64 / width as f64) * 3.0 - 2.0;
            output = output.wrapping_add(mandelbrot(c_re, c_im, max_iter) as u64);
        }
    }
    // Print to prevent the compiler from optimizing the whole calculation away
    println!("Checksum: {}", output);
}